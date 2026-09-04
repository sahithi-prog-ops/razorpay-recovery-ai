import os
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score,
)

import joblib


# --------------------------------------------------
# 1. Paths
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "payments.csv"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "recovery_model.pkl"
)


# --------------------------------------------------
# 2. Load dataset
# --------------------------------------------------

df = pd.read_csv(DATA_PATH)

print("Dataset loaded successfully")
print("Rows:", len(df))
print("Columns:", list(df.columns))


# --------------------------------------------------
# 3. Feature definitions
# --------------------------------------------------

NUMERICAL_FEATURES = [
    "amount",
    "retry_count",
    "successful_payments",
    "failed_payments",
    "lifetime_value",
    "subscription_active",
    "previous_failures",

    # Metadata numeric features
    "international",
    "contact_present",
    "acquirer_transaction_present",
    "cart_session_duration_seconds",
]


CATEGORICAL_FEATURES = [
    "failure_reason",

    # Razorpay metadata
    "bank",
    "wallet",
    "error_code",
    "error_source",
    "error_step",
    "error_reason",
    "checkout_device",
    "user_preferred_language",
]


ALL_FEATURES = (
    NUMERICAL_FEATURES +
    CATEGORICAL_FEATURES
)


# --------------------------------------------------
# 4. Make sure missing columns exist
# --------------------------------------------------

for column in ALL_FEATURES:

    if column not in df.columns:

        if column in CATEGORICAL_FEATURES:
            df[column] = "UNKNOWN"

        else:
            df[column] = 0


# --------------------------------------------------
# 5. Normalize categorical columns
# --------------------------------------------------

for column in CATEGORICAL_FEATURES:

    df[column] = (
        df[column]
        .fillna("UNKNOWN")
        .astype(str)
    )


# --------------------------------------------------
# 6. Normalize numerical columns
# --------------------------------------------------

for column in NUMERICAL_FEATURES:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0)


# --------------------------------------------------
# 7. Separate features and target
# --------------------------------------------------

X = df[ALL_FEATURES]

y = df["recovered"]


# --------------------------------------------------
# 8. Preprocessor
# --------------------------------------------------

preprocessor = ColumnTransformer(
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
            NUMERICAL_FEATURES,
        ),
    ]
)


# --------------------------------------------------
# 9. Model
# --------------------------------------------------

model = Pipeline(
    steps=[

        (
            "preprocessor",
            preprocessor
        ),

        (
            "classifier",
            LogisticRegression(
                max_iter=1000
            )
        ),
    ]
)


# --------------------------------------------------
# 10. Train/test split
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(

    X,
    y,

    test_size=0.2,

    random_state=42,

    stratify=y,
)


print("\nTraining records:", len(X_train))
print("Testing records:", len(X_test))


# --------------------------------------------------
# 11. Train
# --------------------------------------------------

print("\nTraining recovery prediction model...")

model.fit(
    X_train,
    y_train
)

print("Model training completed.")


# --------------------------------------------------
# 12. Predictions
# --------------------------------------------------

predictions = model.predict(
    X_test
)

probabilities = model.predict_proba(
    X_test
)[:, 1]


# --------------------------------------------------
# 13. Evaluation
# --------------------------------------------------

accuracy = accuracy_score(
    y_test,
    predictions
)

auc = roc_auc_score(
    y_test,
    probabilities
)


print("\n-----------------------------")
print("MODEL PERFORMANCE")
print("-----------------------------")

print(
    "Accuracy:",
    round(accuracy, 4)
)

print(
    "ROC-AUC:",
    round(auc, 4)
)


print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions
    )
)


# --------------------------------------------------
# 14. Save model
# --------------------------------------------------

joblib.dump(
    model,
    MODEL_PATH
)


print("\nModel saved successfully:")
print(MODEL_PATH)