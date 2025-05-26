import paypalrestsdk
from django.conf import settings

def get_paypal_client():
    """
    Configures and returns an initialized PayPal SDK client.
    Reads PAYPAL_MODE, PAYPAL_CLIENT_ID, and PAYPAL_CLIENT_SECRET from Django settings.
    """
    try:
        paypalrestsdk.configure({
            "mode": settings.PAYPAL_MODE,  # "sandbox" or "live"
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET
        })
        return paypalrestsdk
    except Exception as e:
        # Log this error appropriately in a real application
        print(f"Error configuring PayPal SDK: {e}")
        # Depending on how critical PayPal is, you might raise an exception
        # or return None to indicate failure to configure.
        # For now, returning None.
        return None
