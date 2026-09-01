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