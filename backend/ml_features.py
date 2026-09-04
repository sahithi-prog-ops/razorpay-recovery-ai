from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
import pandas as pd


def encode_features(feature_dict):
    """
    Convert one payment's feature dictionary
    into an ML-ready matrix.
    """

    df = pd.DataFrame([feature_dict])

    matrix = preprocessor.fit_transform(df)

    return matrix

# =========================================================
# FEATURES USED BY THE ML MODEL
# =========================================================

NUMERIC_FEATURES = [
    "international",
    "contact_present",
    "acquirer_transaction_present",
    "cart_session_duration_seconds",
]


CATEGORICAL_FEATURES = [
    "bank",
    "wallet",
    "error_code",
    "error_source",
    "error_step",
    "error_reason",
    "checkout_device",
    "user_preferred_language",
]


# =========================================================
# CREATE ENCODER
# =========================================================

def create_feature_encoder():
    """
    Creates a scikit-learn preprocessing pipeline.

    Numeric features remain numeric.

    Categorical features such as:
        HDFC
        Android
        INCORRECT_OTP

    are converted into numerical one-hot encoded values.
    """

    encoder = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                CATEGORICAL_FEATURES,
            ),
            (
                "numeric",
                "passthrough",
                NUMERIC_FEATURES,
            ),
        ]
    )

    return encoder