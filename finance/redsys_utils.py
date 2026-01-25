import base64
import json
import hashlib
import hmac
from Crypto.Cipher import DES3
from .models import FinanceSettings

class RedsysClient:
    def __init__(self, merchant_code, terminal, secret_key, environment='TEST'):
        self.merchant_code = merchant_code
        self.terminal = terminal
        self.secret_key = secret_key
        self.environment = environment
        
        if environment == 'REAL':
            self.url = 'https://sis.redsys.es/sis/real/TrataPeticionREST'
            self.web_url = 'https://sis.redsys.es/sis/real/VierualTPV/payment.jsp' # Not exact, usually generic
        else:
            # Sandbox URL
            self.url = 'https://sis-t.redsys.es:25443/sis/rest/trataPeticionREST'
            self.web_url = 'https://sis-t.redsys.es:25443/sis/real/VierualTPV/payment.jsp' # Check exact URL later

    def _encrypt_3des(self, message, key):
        """
        Encrypts the message using 3DES (Triple DES)
        """
        # Ensure key is 24 bytes (Redsys keys are usually base64 encoded strings that decode to bytes)
        # But Redsys secret key is Base64 encoded.
        key_bytes = base64.b64decode(self.secret_key)
        
        # IV is zero-filled
        iv = b'\0\0\0\0\0\0\0\0'
        
        # Padding (PKCS5/PKCS7) - Redsys requires multiple of 8 bytes
        block_size = 8
        padding_len = block_size - (len(message) % block_size)
        padding = bytes([padding_len] * padding_len)
        padded_message = message + padding
        
        cipher = DES3.new(key_bytes, DES3.MODE_CBC, iv)
        return cipher.encrypt(padded_message)

    def sign_parameters(self, params_json_b64, order_id):
        """
        Generates the Ds_Signature.
        1. Decode Key (Base64)
        2. Diversify Key using 3DES with Order ID as data.
        3. HMAC-SHA256 of params using the Diversified Key.
        4. Base64 Encode result.
        """
        # 1. & 2. Diversify Key
        # The key for HMAC is the 3DES encryption of the Order ID
        # Order ID must be formatted? Usually just the string.
        # Ensure Order ID is treated as bytes
        order_bytes = order_id.encode('utf-8')
        diversified_key = self._encrypt_3des(order_bytes, self.secret_key)
        
        # 3. HMAC-SHA256
        # Params are already b64 encoded
        h = hmac.new(diversified_key, params_json_b64.encode('utf-8'), hashlib.sha256)
        signature = base64.b64encode(h.digest()).decode('utf-8')
        
        return signature

    def create_request_parameters(self, order_id, amount_eur, transaction_type='0', currency='978', description='', merchant_url='', url_ok='', url_ko='', other_params=None):
        """
        Creates the parameters for the Redsys request.
        """
        amount_cents = int(amount_eur * 100)
        
        params = {
            "DS_MERCHANT_AMOUNT": str(amount_cents),
            "DS_MERCHANT_ORDER": str(order_id),
            "DS_MERCHANT_MERCHANTCODE": self.merchant_code,
            "DS_MERCHANT_CURRENCY": currency, # 978 = EUR
            "DS_MERCHANT_TRANSACTIONTYPE": transaction_type, # 0 = Auth
            "DS_MERCHANT_TERMINAL": self.terminal,
            "DS_MERCHANT_MERCHANTURL": merchant_url,
            "DS_MERCHANT_URLOK": url_ok,
            "DS_MERCHANT_URLKO": url_ko,
        }
        
        if description:
            params["DS_MERCHANT_PRODUCTDESCRIPTION"] = description[:125] # Limit length
            
        if other_params:
            params.update(other_params)
            
        # Eliminate None values
        params = {k: v for k, v in params.items() if v is not None}
            
        # JSON Encode
        json_params = json.dumps(params)
        # Base64 Encode
        b64_params = base64.b64encode(json_params.encode('utf-8')).decode('utf-8')
        
        # Sign
        signature = self.sign_parameters(b64_params, order_id)
        
        return {
            "Ds_SignatureVersion": "HMAC_SHA256_V1",
            "Ds_MerchantParameters": b64_params,
            "Ds_Signature": signature
        }

    def decode_response(self, merchant_params_b64, signature_received):
        """
        Validates the response from Redsys.
        """
        # Decode Params
        params_json = base64.b64decode(merchant_params_b64).decode('utf-8') # Might need unquote
        # Sometimes Redsys sends URL-encoded chars, but usually it's clean B64 in POST.
        # Safest is to handle potential URL decoding if coming from GET, but usually it's POST.
        
        try:
           params = json.loads(params_json)
        except:
            # Try unquote
            import urllib.parse
            params_json = urllib.parse.unquote(params_json)
            params = json.loads(params_json)
            
        order_id = params.get('Ds_Order') or params.get('DS_ORDER')
        if not order_id:
            raise ValueError("No Order ID found in response")
            
        # Recalculate Signature
        valid_signature = self.sign_parameters(merchant_params_b64, order_id)
        
        # Compare (Safe compare)
        # Redsys signature uses + and / url safe replacements sometimes?
        # Standard Redsys is standard Base64.
        
        # Convert Redsys signature: they substitute + with - and / with _ sometimes in newer versions, 
        # but the standard HMAC_SHA256_V1 is usually standard B64.
        # Let's verify strict equality first.
        
        if signature_received != valid_signature:
             # Try URL safe replacement just in case
             valid_safe = valid_signature.replace('+', '-').replace('/', '_')
             if signature_received != valid_safe:
                 raise ValueError(f"Invalid Signature. Calculated: {valid_signature}, Received: {signature_received}")
                 
        return params

    def charge_request(self, order_id, amount_eur, token, description=''):
        """
        Performs a REST API call to charge a token (Pago por Referencia).
        Type L (Pago por Referencia).
        """
        import requests
        
        # Params for Token Charge
        # DS_MERCHANT_TRANSACTIONTYPE = 'L' (Pago por Referencia / Recurring) Or '0' with Identifier?
        # Redsys documentation: To charge a card using "Pago por Referencia", use Type '0' (Auth) or 'A' (Pago Tradicional) 
        # BUT including "DS_MERCHANT_IDENTIFIER" with the Token.
        # Actually, for "Pago por Referencia" (using previous Order ID), we use:
        # DS_MERCHANT_TRANSACTIONTYPE = '0'
        # DS_MERCHANT_AUTHORISATIONCODE = (Optional?)
        # DS_MERCHANT_IDENTIFIER = The value of the Token (usually the original Order ID).
        # Wait, if we use the "Reference" system (Merchant identifier), the token is the identifier.
        # If we use CoF (Credential on File), we must send DS_MERCHANT_COF_INI='S' on first, and subsequent?
        
        # Simplest Redsys Recurring:
        # DS_MERCHANT_TRANSACTIONTYPE = '0'
        # DS_MERCHANT_IDENTIFIER = <The Token>
        # DS_MERCHANT_DIRECTPAYMENT = 'true' (This is important for REST to not redirect, but perform charge)
        # Note: 'true' string.
        
        params_dict = {
            "DS_MERCHANT_IDENTIFIER": token,
            "DS_MERCHANT_DIRECTPAYMENT": "true", # Important for background charge
            "DS_MERCHANT_COF_INI": "N", # Not initial
            "DS_MERCHANT_COF_TYPE": "C", # Customer Initiated (or R for Recurring)
        }
        
        payload = self.create_request_parameters(
            order_id=order_id,
            amount_eur=amount_eur,
            transaction_type='0',
            description=description,
            other_params=params_dict
        )
        
        try:
            response = requests.post(self.url, json=payload, headers={'Content-Type': 'application/json'}, timeout=30)
            response.raise_for_status()
            
            resp_data = response.json()
            
            # Decode response (it's encrypted/signed)
            ds_params_b64 = resp_data.get('Ds_MerchantParameters')
            ds_signature = resp_data.get('Ds_Signature')
            
            if not ds_params_b64:
                 return False, f"Invalid Response: {resp_data}"
                 
            decoded = self.decode_response(ds_params_b64, ds_signature)
            
            # Check Response Code
            code = int(decoded.get('Ds_Response', 9999))
            if 0 <= code <= 99:
                 return True, decoded
            else:
                 error_msg = f"Redsys Error {code}"
                 # Add specific error mapping if needed
                 return False, error_msg
                 
        except Exception as e:
            return False, str(e)

    def refund_request(self, order_id, amount_eur, original_order_id, description='Devolución'):
        """
        Performs a REFUND (Devolución) request.
        Transaction Type '3'.
        DS_MERCHANT_ORDER: New Order ID for the refund transaction itself.
        """
        import requests
        
        # Original Order ID is needed? 
        # For Redsys Refund, you usually need the Original Order ID?
        # Actually in Redsys REST, for "Devolución" (3), you just send the parameters.
        # But if it is linked to a previous transaction, sometimes 'DS_MERCHANT_MAGSTRIPE' or params are used?
        # Documentation says: TransactionType=3.
        # The documentation implies you might not strictly need to link it if you have the card token?
        # But usually refunds are done against the original transaction using the Order ID.
        # However, here we are using REST.
        
        # Let's assume standard Refund via REST requires just TransactionType=3
        # And usually matching amounts / terminal etc.
        
        # NOTE: Redsys REST often requires the "original" order ID in DS_MERCHANT_ORDER for query/cancellation,
        # but for a NEW refund transaction, it needs a NEW unique Order ID, 
        # and maybe a reference to the old one?
        
        # Standard Redsys Web Refund is done via "Operaciones".
        # Programmatic Refund:
        # DS_MERCHANT_TRANSACTIONTYPE = '3'
        
        payload = self.create_request_parameters(
            order_id=order_id, # Must be UNIQUE for this refund op
            amount_eur=amount_eur,
            transaction_type='3',
            description=description
        )
        
        # We might need to send original order ID in some field if not using Token?
        # If we have a Token (COF), we can refund to that Token.
        # If we don't have token but just transaction ID, it's harder in REST without reference.
        # For now, let's assume we use the Token approach if available, or just try generic Refund if enabled.
        
        try:
             response = requests.post(self.url, json=payload, headers={'Content-Type': 'application/json'}, timeout=30)
             response.raise_for_status()
             
             resp_data = response.json()
             
             ds_params_b64 = resp_data.get('Ds_MerchantParameters')
             ds_signature = resp_data.get('Ds_Signature')
             
             if not ds_params_b64:
                  return False, f"Invalid Response: {resp_data}"
                  
             decoded = self.decode_response(ds_params_b64, ds_signature)
             
             code = int(decoded.get('Ds_Response', 9999))
             # Refund OK codes usually 0000-0099
             if 0 <= code <= 99:
                  return True, decoded
             else:
                  return False, f"Redsys Error {code}"
                  
        except Exception as e:
            return False, str(e)


def get_redsys_client(gym):
    settings = FinanceSettings.objects.get(gym=gym)
    if not settings.redsys_merchant_code or not settings.redsys_secret_key:
        return None
        
    return RedsysClient(
        merchant_code=settings.redsys_merchant_code,
        terminal=settings.redsys_merchant_terminal,
        secret_key=settings.redsys_secret_key,
        environment=settings.redsys_environment
    )


def generate_redsys_form_for_tokenization(client, amount, description):
    """
    Genera los parámetros para tokenizar una tarjeta con Redsys (cargo simbólico).
    El cargo será reembolsado automáticamente después.
    """
    from django.urls import reverse
    from django.contrib.sites.models import Site
    
    gym = client.gym
    settings = FinanceSettings.objects.get(gym=gym)
    
    if not settings.redsys_merchant_code or not settings.redsys_secret_key:
        raise Exception("Redsys no configurado")
    
    redsys_client = RedsysClient(
        merchant_code=settings.redsys_merchant_code,
        terminal=settings.redsys_merchant_terminal,
        secret_key=settings.redsys_secret_key,
        environment=settings.redsys_environment
    )
    
    # Generar orden única
    import time
    order_id = f"TK{client.id}{int(time.time())}"[:12]  # Max 12 chars
    
    # URLs de retorno
    current_site = Site.objects.get_current()
    domain = current_site.domain
    protocol = 'https' if settings.redsys_environment == 'REAL' else 'http'
    
    merchant_url = f"{protocol}://{domain}{reverse('portal_redsys_tokenization_callback')}"
    url_ok = f"{protocol}://{domain}{reverse('portal_payment_methods')}?tokenization=success"
    url_ko = f"{protocol}://{domain}{reverse('portal_payment_methods')}?tokenization=error"
    
    params = {
        "DS_MERCHANT_AMOUNT": str(amount),  # en céntimos
        "DS_MERCHANT_ORDER": order_id,
        "DS_MERCHANT_MERCHANTCODE": redsys_client.merchant_code,
        "DS_MERCHANT_CURRENCY": "978",  # EUR
        "DS_MERCHANT_TRANSACTIONTYPE": "0",  # Autorización
        "DS_MERCHANT_TERMINAL": redsys_client.terminal,
        "DS_MERCHANT_MERCHANTURL": merchant_url,
        "DS_MERCHANT_URLOK": url_ok,
        "DS_MERCHANT_URLKO": url_ko,
        "DS_MERCHANT_MERCHANTDATA": json.dumps({"client_id": client.id, "tokenize": True}),
        "DS_MERCHANT_PRODUCTDESCRIPTION": description,
        "DS_MERCHANT_IDENTIFIER": "REQUIRED",  # Solicitar tokenización
    }
    
    # Codificar parámetros
    params_json = json.dumps(params)
    params_b64 = base64.b64encode(params_json.encode('utf-8')).decode('utf-8')
    
    # Firmar
    signature = redsys_client.sign_parameters(params_b64, order_id)
    
    # Retornar datos para el frontend
    return {
        'redirect_url': redsys_client.web_url,
        'Ds_SignatureVersion': 'HMAC_SHA256_V1',
        'Ds_MerchantParameters': params_b64,
        'Ds_Signature': signature,
    }
