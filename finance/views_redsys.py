import json
import uuid
import datetime
import logging
import hmac
import hashlib
import base64
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

# Security logger for payment events
security_logger = logging.getLogger('django.security')

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
    
    SECURITY: 
    - Validates signature BEFORE processing any data
    - Logs all payment attempts for audit
    - Sanitizes error messages
    """
    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)
    
    # Get client IP for logging
    client_ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', 'unknown')
    
    ds_params_b64 = request.POST.get('Ds_MerchantParameters')
    ds_signature = request.POST.get('Ds_Signature')
    
    if not ds_params_b64 or not ds_signature:
        security_logger.warning(f"Redsys webhook missing params from IP: {client_ip}")
        return HttpResponse("Missing params", status=400)

    # SECURITY: Validate signature by trying all configured merchants
    # This ensures we don't process unverified data
    validated_params = None
    matched_settings = None
    
    for settings in FinanceSettings.objects.filter(redsys_secret_key__isnull=False).exclude(redsys_secret_key=''):
        try:
            redsys_client = get_redsys_client(settings.gym)
            if redsys_client:
                # This will raise an exception if signature is invalid
                validated_params = redsys_client.decode_response(ds_params_b64, ds_signature)
                matched_settings = settings
                break
        except Exception:
            # Signature didn't match this merchant, try next
            continue
    
    if not validated_params:
        security_logger.warning(
            f"Redsys webhook invalid signature from IP: {client_ip}"
        )
        return HttpResponse("Invalid signature", status=403)
    
    try:
        # SECURITY: Now we can safely process the validated data
        response_code = int(validated_params.get('Ds_Response', 9999))
        merchant_code = validated_params.get('Ds_MerchantCode', '')
        order_id = validated_params.get('Ds_Order', '')
        
        # Log all payment attempts
        security_logger.info(
            f"Redsys payment notification: order={order_id}, "
            f"response={response_code}, merchant={merchant_code}, ip={client_ip}"
        )
        
        # Redsys 0000-0099 are auth OK.
        if 0 <= response_code <= 99:
            client_id = validated_params.get('Ds_MerchantData')
            
            # SECURITY: Validate client exists and belongs to the correct gym
            try:
                client = Client.objects.get(pk=client_id, gym=matched_settings.gym)
            except Client.DoesNotExist:
                security_logger.error(
                    f"Redsys webhook client mismatch: client_id={client_id}, "
                    f"gym={matched_settings.gym.id}, order={order_id}"
                )
                return HttpResponse("Client mismatch", status=400)
            
            # Get token info
            token = validated_params.get('Ds_Merchant_Identifier')
            if not token:
                token = validated_params.get('Ds_Order')
            
            card_number = validated_params.get('Ds_Card_Number', '')  # ****1234
            expiration = validated_params.get('Ds_ExpiryDate', '') 
            brand = validated_params.get('Ds_Card_Brand', '')
            
            # Create Token
            ClientRedsysToken.objects.create(
                client=client,
                token=token,
                card_number=card_number,
                expiration=expiration,
                card_brand=brand
            )
            
            security_logger.info(
                f"Redsys card saved successfully: client={client_id}, order={order_id}"
            )
            
            return HttpResponse("OK")
        else:
            security_logger.info(
                f"Redsys payment denied: order={order_id}, response={response_code}"
            )
            return HttpResponse("KO: Transaction Denied")
            
    except Exception as e:
        # SECURITY: Don't expose internal errors
        security_logger.exception(f"Redsys webhook error: {str(e)}")
        return HttpResponse("Internal Error", status=500)

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
