import hmac
import hashlib
import os
import requests
from dotenv import load_dotenv

load_dotenv("backend/.env")

body = '{"event":"payment.failed","payload":{"payment":{"entity":{"id":"test_payment","amount":49900,"currency":"INR","method":"card","status":"failed"}}}}'

secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

if not secret:
    raise RuntimeError("RAZORPAY_WEBHOOK_SECRET not loaded")

signature = hmac.new(
    secret.encode("utf-8"),
    body.encode("utf-8"),
    hashlib.sha256
).hexdigest()

print("Webhook secret loaded:", True)
print("Body:", body)
print("Generated signature:", signature)

response = requests.post(
    "http://127.0.0.1:8000/webhook/razorpay",
    data=body.encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "X-Razorpay-Signature": signature
    }
)

print("HTTP status:", response.status_code)
print("Response:", response.text)
