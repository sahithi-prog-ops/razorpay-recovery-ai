from backend.metadata_extractor import extract_payment_metadata
from backend.feature_engineering import build_features


sample_payment = {
    "id": "pay_demo_metadata",
    "amount": 90233,
    "currency": "INR",
    "status": "failed",

    "error_code": "BAD_REQUEST_ERROR",
    "error_source": "customer",
    "error_step": "payment_authentication",
    "error_reason": "incorrect_otp",

    "network": {
        "bank": "HDFC",
        "wallet": None,
        "vpa": None,
        "acquirer_data": {
            "bank_transaction_id": "0125836177"
        }
    },

    "international": False,
    "contact": "+919999999999",
    "email": "customer@example.com",

    "notes": {
        "checkout_device": "Android",
        "cart_session_duration_seconds": 42,
        "user_preferred_language": "en-IN"
    }
}


metadata = extract_payment_metadata(sample_payment)

features = build_features(
    metadata,
    sample_payment
)


print("\nEXTRACTED METADATA")
print("=" * 50)

for key, value in metadata.items():
    print(f"{key}: {value}")


print("\nML FEATURES")
print("=" * 50)

for key, value in features.items():
    print(f"{key}: {value}")