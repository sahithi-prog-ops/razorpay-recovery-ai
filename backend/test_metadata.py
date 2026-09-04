from feature_engineering import build_features


sample_metadata = {
    "network": {
        "bank": "HDFC",
        "wallet": None,
        "vpa": None,
        "acquirer_data": {
            "bank_transaction_id": "0125836177"
        }
    },

    "user": {
        "international": False,
        "contact": "+919999999999",
        "email": "customer@example.com"
    },

    "merchant_notes": {
        "checkout_device": "Android",
        "cart_session_duration_seconds": 42,
        "user_preferred_language": "en-IN"
    }
}


sample_payment = {
    "error_code": "BAD_REQUEST_ERROR",
    "error_source": "customer",
    "error_step": "payment_authentication",
    "error_reason": "incorrect_otp"
}


features = build_features(
    sample_metadata,
    sample_payment
)


print("\nML FEATURES")
print("=" * 50)

for key, value in features.items():
    print(f"{key}: {value}")