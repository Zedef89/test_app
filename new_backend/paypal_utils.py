# new_backend/paypal_utils.py
from . import config
import uuid

class MockPayPalClient:
    def __init__(self, client_id, client_secret, mode):
        self.client_id = client_id
        self.client_secret = client_secret
        self.mode = mode

    def payment_create(self, payment_data: dict):
        # Simulate payment creation
        # In a real scenario, this would involve API calls to PayPal
        # For now, just return a mock response structure
        mock_paypal_payment_id = "PAYID-" + str(uuid.uuid4())
        approval_url = None
        # Simplified search for internal_transaction_id in the return_url
        # In a real scenario, PayPal's response structure is more complex.
        return_url_str = payment_data.get("redirect_urls", {}).get("return_url", "")
        
        # A more robust way to ensure internal_transaction_id is part of the approval URL.
        # The provided snippet for approval_url construction was a bit basic.
        # Let's assume the return_url from payment_data already correctly includes our internal_transaction_id.
        # The mock just needs to append PayPal's mock identifiers.
        if "internal_transaction_id" in return_url_str:
             approval_url = f"{return_url_str}&mockPaymentId={mock_paypal_payment_id}&PayerID=MOCKPAYERID"
        else: # Fallback, though ideally internal_transaction_id should always be in return_url
             approval_url = f"{return_url_str}?internal_transaction_id=UNKNOWN&mockPaymentId={mock_paypal_payment_id}&PayerID=MOCKPAYERID"


        return {
            "id": mock_paypal_payment_id,
            "state": "created",
            "links": [{"rel": "approval_url", "href": approval_url}]
        }, True # True indicates success

    def payment_execute(self, payment_id: str, payer_id: str):
        # Simulate payment execution
        mock_paypal_transaction_id = "SALE-" + str(uuid.uuid4())
        return {
            "id": payment_id,
            "state": "approved", # Or "completed"
            "transactions": [{"related_resources": [{"sale": {"id": mock_paypal_transaction_id}}]}]
        }, True # True indicates success
        
    def payment_find(self, payment_id: str): # For finding payment details
        # Simulates finding a payment. In a real scenario, this would check PayPal.
        # For mock, assume it's always found in 'created' state if not executed.
        return {"id": payment_id, "state": "created"}, True


_paypal_client = None

def get_paypal_client():
    global _paypal_client
    if _paypal_client is None:
        # In a real app, use PayPalSDK or similar
        _paypal_client = MockPayPalClient(
            client_id=config.PAYPAL_CLIENT_ID,
            client_secret=config.PAYPAL_CLIENT_SECRET,
            mode=config.PAYPAL_MODE
        )
    return _paypal_client

def create_paypal_payment(client: MockPayPalClient, amount_str: str, currency: str, return_url: str, cancel_url: str, description: str, internal_transaction_id: str):
    # The return_url and cancel_url passed here are the base paths from config.
    # We append internal_transaction_id here to ensure it's part of the URLs PayPal uses for redirection.
    
    # Construct full redirect URLs with internal_transaction_id
    # APP_BASE_URL needs to be considered if not already part of return_url/cancel_url paths
    # Assuming return_url and cancel_url are full paths like "/payment/success"
    
    # If return_url and cancel_url are just paths, construct full URLs
    # Example: "http://localhost:8000/payment/success?internal_transaction_id=123"
    # The task description for config has PAYPAL_RETURN_URL_PATH. So we need to combine.
    
    full_return_url = f"{config.APP_BASE_URL.rstrip('/')}{config.PAYPAL_RETURN_URL_PATH}?internal_transaction_id={internal_transaction_id}"
    full_cancel_url = f"{config.APP_BASE_URL.rstrip('/')}{config.PAYPAL_CANCEL_URL_PATH}?internal_transaction_id={internal_transaction_id}"

    payment_data = {
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": full_return_url,
            "cancel_url": full_cancel_url
        },
        "transactions": [{
            "amount": {"total": amount_str, "currency": currency},
            "description": description
        }]
    }
    response, success = client.payment_create(payment_data)
    if success:
        approval_url_found = None
        for link in response.get("links", []):
            if link.get("rel") == "approval_url":
                approval_url_found = link.get("href")
                break
        return response.get("id"), approval_url_found # Returns PayPal's PAYID-xxx and the approval URL
    return None, None


def execute_paypal_payment_simulation(client: MockPayPalClient, payment_id: str, payer_id: str):
    response, success = client.payment_execute(payment_id, payer_id)
    if success and response.get("state") == "approved": # or "completed"
        # Extract the sale ID (PayPal transaction ID)
        try:
            sale_id = response["transactions"][0]["related_resources"][0]["sale"]["id"]
            return sale_id, "completed" # Return PayPal's SALE-xxx and our 'completed' status
        except (IndexError, KeyError) as e:
            print(f"Error parsing PayPal execution response: {e}")
            return None, "failed" # Or some other status indicating parsing issue
    return None, "failed"
