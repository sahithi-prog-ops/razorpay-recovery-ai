from metadata_extractor import extract_payment_metadata


sample_payment = {
    "id": "pay_test_001",
    "amount": 50000,
    "currency": "INR",
    "method": "netbanking",
    "bank": "HDFC",
    "wallet": None,
    "international": False,
    "email": "customer@example.com",
    "contact": "+919876543210",

    "error_code": "BAD_REQUEST_ERROR",
    "error_description": "Payment processing failed because of incorrect OTP",
    "error_source": "customer",
    "error_step": "payment_authentication",
    "error_reason": "incorrect_otp",

    "acquirer_data": {
        "bank_transaction_id": "0125836177"
    },

    "notes": {
        "checkout_device": "Android",
        "cart_session_duration_seconds": "42",
        "user_preferred_language": "en-IN"
    }
}


result = extract_payment_metadata(sample_payment)

print(result)