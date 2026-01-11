import stripe
from django.conf import settings
from .models import FinanceSettings

def get_keys(gym):
    """Retrieve Stripe keys for a Gym."""
    try:
        finance = gym.finance_settings
        return finance.stripe_public_key, finance.stripe_secret_key
    except FinanceSettings.DoesNotExist:
        return None, None

def get_stripe_customer(client):
    """
    Get or create a Stripe Customer for the given Client.
    Returns the Stripe Customer ID.
    """
    pub_key, secret_key = get_keys(client.gym)
    if not secret_key:
        raise ValueError("Stripe not configured for this gym.")
    
    stripe.api_key = secret_key
    
    if client.stripe_customer_id:
        try:
            # Verify it exists
            customer = stripe.Customer.retrieve(client.stripe_customer_id)
            if not customer.get('deleted'):
                return client.stripe_customer_id
        except stripe.error.InvalidRequestError:
            pass # Invalid ID, recreate

    # Create new customer
    customer = stripe.Customer.create(
        email=client.email,
        name=f"{client.first_name} {client.last_name}",
        metadata={
            'client_id': client.id,
            'gym_id': client.gym.id,
            'gym_name': client.gym.name
        }
    )
    
    client.stripe_customer_id = customer.id
    client.save(update_fields=['stripe_customer_id'])
    return customer.id

def create_setup_intent(client):
    """
    Create a SetupIntent for saving a card.
    Returns the client_secret.
    """
    pub_key, secret_key = get_keys(client.gym)
    if not secret_key:
        raise ValueError("Stripe not configured.")
        
    stripe.api_key = secret_key
    customer_id = get_stripe_customer(client)
    
    intent = stripe.SetupIntent.create(
        customer=customer_id,
        payment_method_types=['card'],
        usage='off_session', # Optimized for future payments
    )
    return intent.client_secret

def list_payment_methods(client):
    """
    List saved cards for a client.
    """
    pub_key, secret_key = get_keys(client.gym)
    if not secret_key:
        return []

    stripe.api_key = secret_key
    
    if not client.stripe_customer_id:
        return []

    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=client.stripe_customer_id,
            type="card"
        )
        return payment_methods.data
    except Exception as e:
        print(f"Error listing methods: {e}")
        return []

def charge_client(client, amount_eur, payment_method_id, description="Venta"):
    """
    Charges a client's saved payment method.
    """
    keys = get_keys(client.gym)
    if not keys:
        raise Exception("Stripe no configurado")
        
    stripe.api_key = keys['secret_key']
    
    # 1. Get Customer ID
    customer_id = get_stripe_customer(client)
    
    # 2. Create PaymentIntent
    intent = stripe.PaymentIntent.create(
        amount=int(amount_eur * 100), # Centimos
        currency=keys['currency'],
        customer=customer_id,
        payment_method=payment_method_id,
        off_session=True,
        confirm=True,
        description=description,
        return_url='https://example.com/return' # Required for some flows
    )
    
    return intent

def validate_keys(public_key, secret_key):
    """
    Validates Stripe keys by making a lightweight API call.
    Returns True if valid, raises Exception if invalid.
    """
    try:
        stripe.api_key = secret_key
        # Retrieve account details (lightweight)
        stripe.Account.retrieve()
        return True
    except stripe.error.AuthenticationError:
        raise Exception("La Clave Secreta no es válida.")
    except Exception as e:
        raise Exception(f"Error al conectar con Stripe: {str(e)}")
