import os
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

import joblib


# --------------------------------------------------
# 1. Load dataset
# --------------------------------------------------

DATA_PATH = "../data/payments.csv"
MODEL_PATH = "recovery_model.pkl"

df = pd.read_csv(DATA_PATH)

print("Dataset loaded successfully")
print("Rows:", len(df))
print("Columns:", list(df.columns))


# --------------------------------------------------
# 2. Separate features and target
# --------------------------------------------------

X = df.drop(columns=["payment_id", "recovered"])

y = df["recovered"]


# --------------------------------------------------
# 3. Identify features
# --------------------------------------------------

numerical_features = [
    "amount",
    "retry_count",
    "successful_payments",
    "failed_payments",
    "lifetime_value",
    "subscription_active",
    "previous_failures",
]

categorical_features = [
    "failure_reason"
]


# --------------------------------------------------
# 4. Preprocessing
# --------------------------------------------------

preprocessor = ColumnTransformer(
    transformers=[
        (
            "categorical",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features
        )
    ],
    remainder="passthrough"
)


# --------------------------------------------------
# 5. Create model pipeline
# --------------------------------------------------

model = Pipeline(
    steps=[
        ("preprocessor", preprocessor),
        (
            "classifier",
            LogisticRegression(max_iter=1000)
        )
    ]
)


# --------------------------------------------------
# 6. Split dataset
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)

print("\nTraining records:", len(X_train))
print("Testing records:", len(X_test))


# --------------------------------------------------
# 7. Train
# --------------------------------------------------

print("\nTraining recovery prediction model...")

model.fit(X_train, y_train)

print("Model training completed.")


# --------------------------------------------------
# 8. Predictions
# --------------------------------------------------

predictions = model.predict(X_test)

probabilities = model.predict_proba(X_test)[:, 1]


# --------------------------------------------------
# 9. Evaluate
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

print("Accuracy:", round(accuracy, 4))
print("ROC-AUC:", round(auc, 4))

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions
    )
)


# --------------------------------------------------
# 10. Save model
# --------------------------------------------------

joblib.dump(
    model,
    MODEL_PATH
)

print("\nModel saved successfully:")
print(os.path.abspath(MODEL_PATH))