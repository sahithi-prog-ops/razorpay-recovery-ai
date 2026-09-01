import sys
import hmac
import hashlib
import os

sys.path.insert(0, "backend")

from dotenv import load_dotenv
import razorpay_service

load_dotenv("backend/.env")

body = '{"event":"payment.failed","payload":{"payment":{"entity":{"id":"test_payment","amount":49900,"currency":"INR","method":"card","status":"failed"}}}}'

secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

print("Secret:", repr(secret))

signature = hmac.new(
    secret.encode("utf-8"),
    body.encode("utf-8"),
    hashlib.sha256
).hexdigest()

print("Signature:", signature)

try:
    result = razorpay_service.verify_webhook_signature(
        body.encode("utf-8"),
        signature
    )
    print("SUCCESS:", result)
except Exception as e:
    print("FAILED:", type(e).__name__)
    print("ERROR:", str(e))
