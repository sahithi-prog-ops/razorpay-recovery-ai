import joblib
import pandas as pd

from backend.feature_engineering import build_features


metadata = {
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


payment = {
    "error_code": "BAD_REQUEST_ERROR",
    "error_source": "customer",
    "error_step": "payment_authentication",
    "error_reason": "incorrect_otp"
}


# Build the 12 raw ML features
features = build_features(
    metadata,
    payment
)

print("\nRAW FEATURES")
print("=" * 50)

for key, value in features.items():
    print(f"{key}: {value}")


# Convert dictionary → one-row DataFrame
X = pd.DataFrame([features])

print("\nDATAFRAME")
print("=" * 50)
print("Shape:", X.shape)
print(X)


# Load trained model
model = joblib.load(
    "ml/recovery_model.pkl"
)

print("\nMODEL")
print("=" * 50)
print("Type:", type(model))
print("Expected features:", model.n_features_in_)


# Run prediction
prediction = model.predict(X)

probability = model.predict_proba(X)

print("\nPREDICTION")
print("=" * 50)
print("Class:", prediction[0])
print("Probability:", probability[0])
print("Recovery probability:", probability[0][1])