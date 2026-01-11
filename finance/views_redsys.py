import json
import uuid
import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib import messages
from django.urls import reverse

from clients.models import Client
from .models import FinanceSettings, ClientRedsysToken
from .redsys_utils import get_redsys_client

def generate_order_id():
    # Redsys Order ID: 4 digits + 8 alphanum. Max 12 chars.
    # Must be unique per transaction.
    # We can use YYDD + 8 random chars.
    now = datetime.datetime.now()
    prefix = now.strftime('%y%j') # Year + Day of Year
    suffix = str(uuid.uuid4().int)[:8]
    return f"{prefix}{suffix}"

@login_required
def redsys_authorize_start(request, client_id):
    """
    Initiates a 0 EUR (or 1 EUR) authorization to save the card.
    Note: Tokenization usually requires a real transaction. 
    Standard practice: Charge 0 EUR if supported, or standard Auth.
    We will use '0' (Authorization) with Amount 0 if allowed, or check bank config.
    Usually we do a 0 Auth or a real auth.
    For simplicity we assume 0 Auth is allowed for verification.
    """
    client = get_object_or_404(Client, pk=client_id)
    # Check permission? request.user...
    
    redsys_client = get_redsys_client(client.gym)
    if not redsys_client:
        messages.error(request, "Redsys no está configurado en este centro.")
        return redirect('client_detail', pk=client_id)

    # Generate unique Order ID
    order_id = generate_order_id()
    
    # Amount 0 for card verification (if supported)
    amount = 0 
    
    # Callback URLs
    # Must be absolute URLs
    domain = request.build_absolute_uri('/')[:-1]
    url_ok = f"{domain}{reverse('redsys_ok')}?client_id={client_id}" 
    url_ko = f"{domain}{reverse('redsys_ko')}?client_id={client_id}"
    merchant_url = f"{domain}{reverse('redsys_notify')}"
    
    # Create Request
    # TransactionType '0' (Authorization)
    # Required for Tokenization: DS_MERCHANT_IDENTIFIER if using identifiers, 
    # but for simple "Reference Payment" (Pago por Referencia), 
    # we just need to keep the Order ID of this transaction.
    # We pass client_id in MerchantData or description to recover it in notify if needed
    
    params = redsys_client.create_request_parameters(
        order_id=order_id,
        amount_eur=amount,
        transaction_type='0', # Authorization
        description=f"Vinculacion Tarjeta {client.id}",
        merchant_url=merchant_url,
        url_ok=url_ok,
        url_ko=url_ko,
        other_params={
             "DS_MERCHANT_DATA": str(client.id), # Pass client ID to retrieve in webhook
             "DS_MERCHANT_COF_INI": "S", # Credential on File Initial (Recurring)
             "DS_MERCHANT_COF_TYPE": "C" # Scheduled or C (Customer Initiated)? 
             # Usually for saving card for future use we signal COF_INI.
        }
    )
    
    context = {
        'url': redsys_client.url,
        'params': params
    }
    
    return render(request, 'backoffice/finance/redsys_redirect.html', context)

@csrf_exempt
def redsys_notify(request):
    """
    Webhook called by Redsys.
    """
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
        
    ds_params_b64 = request.POST.get('Ds_MerchantParameters')
    ds_signature = request.POST.get('Ds_Signature')
    
    if not ds_params_b64 or not ds_signature:
         return HttpResponse("Missing params", status=400)

    # We don't have gym info easily if multiple gyms use same endpoint...
    # But usually MerchantCode is unique per gym.
    # We need to find the gym/settings via MerchantCode found in params?
    # Or iterate settings.
    # For now assume single tenant or we decode first to get MerchantCode.
    
    try:
        # Decode without verifying signature first to find the Merchant (Gym)
        # Or try to decode with a generic util? 
        # Actually our Decode relies on Key.
        # Check settings
        import base64
        params_json = base64.b64decode(ds_params_b64).decode('utf-8')
        params_raw = json.loads(params_json)
        merchant_code = params_raw.get('Ds_MerchantCode') or params_raw.get('DS_MERCHANT_MERCHANTCODE')
        
        settings = FinanceSettings.objects.filter(redsys_merchant_code=merchant_code).first()
        if not settings:
            return HttpResponse("Merchant not found", status=404)
        
        redsys_client = get_redsys_client(settings.gym)
        
        # Now Validate Signature
        params = redsys_client.decode_response(ds_params_b64, ds_signature)
        
        # Process Success
        response_code = int(params.get('Ds_Response', 9999))
        
        # Redsys 0000-0099 are auth OK.
        if 0 <= response_code <= 99:
            # OK
            client_id = params.get('Ds_MerchantData')
            client = Client.objects.get(pk=client_id)
            
            # Save Token
            # Usually the TOKEN is the Identifier if returned, or we rely on OrderId if PagoReferencia.
            # DS_MERCHANT_IDENTIFIER usually returned if Identifier configured.
            # If not, we store Order ID.
            
            token = params.get('Ds_Merchant_Identifier') # If enabled
            if not token:
                # Fallback to Pago por Referencia logic: We use the Order ID of THIS transaction
                token = params.get('Ds_Order')
            
            card_number = params.get('Ds_Card_Number', '') # ****1234
            expiration = params.get('Ds_ExpiryDate', '') 
            brand = params.get('Ds_Card_Brand', '')
            
            # Create/Update Token
            # If we want to allow multiple, create new.
            ClientRedsysToken.objects.create(
                client=client,
                token=token,
                card_number=card_number,
                expiration=expiration,
                card_brand=brand
            )
            
            return HttpResponse("OK")
        else:
            return HttpResponse("KO: Transaction Denied")
            
    except Exception as e:
        print(f"Redsys Error: {e}")
        return HttpResponse(f"Error: {e}", status=500)

def redsys_ok(request):
    client_id = request.GET.get('client_id')
    messages.success(request, "Tarjeta vinculada correctamente en Redsys.")
    if client_id:
         return redirect('client_detail', pk=client_id)
    return redirect('dashboard')

def redsys_ko(request):
    client_id = request.GET.get('client_id')
    messages.error(request, "Error al vincular la tarjeta en Redsys.")
    if client_id:
         return redirect('client_detail', pk=client_id)
    return redirect('dashboard')
