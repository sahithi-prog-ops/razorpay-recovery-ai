import pandas as pd
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score


# =========================================================
# 1. LOAD DATA
# =========================================================

DATA_PATH = "data/recovery_training.csv"
MODEL_PATH = "ml/recovery_model.pkl"

df = pd.read_csv(DATA_PATH)

print("\nDataset loaded")
print("Rows:", len(df))
print("Columns:", list(df.columns))


# =========================================================
# 2. CLEAN COLUMN NAMES
# =========================================================

df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)


# =========================================================
# 3. CLEAN STRING VALUES
# =========================================================

for column in df.select_dtypes(include="object").columns:
    df[column] = (
        df[column]
        .astype(str)
        .str.strip()
        .str.replace("*", "", regex=False)
    )


# =========================================================
# 4. TARGET
# =========================================================

TARGET = "recovered"

if TARGET not in df.columns:
    raise ValueError(
        f"Target column '{TARGET}' not found."
    )

X = df.drop(columns=[TARGET])
y = df[TARGET].astype(int)


# =========================================================
# 5. FEATURE TYPES
# =========================================================

numeric_features = [
    "international",
    "contact_present",
    "acquirer_transaction_present",
    "cart_session_duration_seconds"
]

categorical_features = [
    "bank",
    "wallet",
    "error_code",
    "error_source",
    "error_step",
    "error_reason",
    "checkout_device",
    "user_preferred_language"
]


# Make sure required columns exist

missing = [
    column
    for column in numeric_features + categorical_features
    if column not in X.columns
]

if missing:
    raise ValueError(
        f"Missing columns: {missing}"
    )


# =========================================================
# 6. PREPROCESSING
# =========================================================

numeric_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(strategy="median")
        ),
        (
            "scaler",
            StandardScaler()
        )
    ]
)


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


preprocessor = ColumnTransformer(
    transformers=[
        (
            "numeric",
            numeric_pipeline,
            numeric_features
        ),
        (
            "categorical",
            categorical_pipeline,
            categorical_features
        )
    ]
)


# =========================================================
# 7. MODEL
# =========================================================

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=10,
    min_samples_leaf=2,
    random_state=42,
    class_weight="balanced"
)


pipeline = Pipeline(
    steps=[
        (
            "preprocessor",
            preprocessor
        ),
        (
            "model",
            model
        )
    ]
)


# =========================================================
# 8. TRAIN / TEST SPLIT
# =========================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# =========================================================
# 9. TRAIN
# =========================================================

print("\nTraining model...")

pipeline.fit(
    X_train,
    y_train
)


# =========================================================
# 10. EVALUATE
# =========================================================

predictions = pipeline.predict(X_test)

accuracy = accuracy_score(
    y_test,
    predictions
)

print("\n==============================")
print("MODEL RESULTS")
print("==============================")

print(
    f"Accuracy: {accuracy:.4f}"
)

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions,
        zero_division=0
    )
)


# =========================================================
# 11. SAVE
# =========================================================

joblib.dump(
    pipeline,
    MODEL_PATH
)

print("\nModel saved to:")
print(MODEL_PATH)