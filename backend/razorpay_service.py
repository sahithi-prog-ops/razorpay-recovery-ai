import os
import razorpay
from dotenv import load_dotenv

load_dotenv(
    os.path.join(
        os.path.dirname(__file__),
        ".env"
    )
)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise RuntimeError(
        "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET "
        "must be configured in backend/.env"
    )

client = razorpay.Client(
    auth=(
        RAZORPAY_KEY_ID,
        RAZORPAY_KEY_SECRET
    )
)


def fetch_payment(payment_id: str):
    """
    Fetch a real payment from Razorpay.
    """

    return client.payment.fetch(payment_id)


def fetch_all_payments(count=20):
    """
    Fetch recent payments from Razorpay.
    """

    return client.payment.all({
        "count": count
    })


def verify_webhook_signature(
    body: bytes,
    signature: str
):
    """
    Verify that the webhook really came from Razorpay.
    """

    webhook_secret = os.getenv(
        "RAZORPAY_WEBHOOK_SECRET"
    )

    if not webhook_secret:
        raise RuntimeError(
            "RAZORPAY_WEBHOOK_SECRET is missing."
        )

    client.utility.verify_webhook_signature(
        body.decode("utf-8"),
        signature,
        webhook_secret
    )

    return True
def verify_payment(payment_id: str, expected_amount: int):
    """
    Fetch a payment from Razorpay and verify that:
    - the payment exists
    - it is captured/authorized successfully
    - the amount matches the expected amount

    expected_amount is in paise.
    """

    try:
        payment = fetch_payment(payment_id)

        actual_amount = int(payment.get("amount", 0))
        status = payment.get("status")

        amount_matches = actual_amount == int(expected_amount)

        successful_status = status in {
            "captured",
            "authorized"
        }

        verified = amount_matches and successful_status

        return {
            "verified": verified,
            "payment_id": payment_id,
            "status": status,
            "expected_amount": int(expected_amount),
            "actual_amount": actual_amount,
            "amount_matches": amount_matches,
            "successful_status": successful_status,
            "payment": payment,
        }

    except Exception as exc:
        return {
            "verified": False,
            "payment_id": payment_id,
            "status": "verification_error",
            "message": str(exc),
        }
def create_recovery_order(
    amount: int,
    currency: str = "INR",
    receipt: str | None = None,
    notes: dict | None = None,
):
    """
    Create a new Razorpay Order for a revenue-recovery attempt.

    amount is in paise.
    This creates a NEW payment opportunity; it does not modify
    the original failed payment.
    """

    if amount <= 0:
        raise ValueError("Recovery amount must be greater than zero.")

    order_data = {
        "amount": int(amount),
        "currency": currency,
    }

    if receipt:
        order_data["receipt"] = receipt

    if notes:
        order_data["notes"] = notes

    return client.order.create(order_data)
def verify_checkout_signature(
    order_id: str,
    payment_id: str,
    signature: str,
):
    """
    Verify Razorpay Standard Checkout payment signature.

    This must happen on the backend.
    """

    client.utility.verify_payment_signature({
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature,
    })

    return True