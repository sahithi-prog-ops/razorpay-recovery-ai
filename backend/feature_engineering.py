from typing import Dict, Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


CATEGORICAL_FEATURES = [
    "method",
    "bank",
    "wallet",
    "error_code",
    "error_source",
    "error_step",
    "error_reason",
    "checkout_device",
    "user_preferred_language",
]

NUMERIC_FEATURES = [
    "amount",
    "international",
    "contact_present",
    "cart_session_duration_seconds",
]


def metadata_to_dataframe(metadata: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert one normalized payment metadata dictionary
    into a one-row DataFrame.
    """

    row = {
        feature: metadata.get(feature)
        for feature in CATEGORICAL_FEATURES + NUMERIC_FEATURES
    }

    return pd.DataFrame([row])


def build_preprocessor():
    """
    Creates the scikit-learn preprocessing pipeline.
    """

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent")
            ),
            (
                "encoder",
                OneHotEncoder(
                    handle_unknown="ignore"
                )
            )
        ]
    )

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median")
            )
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "categorical",
                categorical_pipeline,
                CATEGORICAL_FEATURES
            ),
            (
                "numeric",
                numeric_pipeline,
                NUMERIC_FEATURES
            )
        ]
    )

    return preprocessor