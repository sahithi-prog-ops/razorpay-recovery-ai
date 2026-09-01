import os

# ---------------------------------------------------------
# Pluggable AI layer
# ---------------------------------------------------------
# The scikit-learn model is completely optional. On some machines
# (locked-down corporate images, Application Control policies, etc.)
# importing scipy/scikit-learn can fail even though nothing else in
# this file needs them. When that happens we fall back to a
# deterministic rule-based MockAIService instead of crashing the whole
# API on import. The API must always be able to start.

AI_ENGINE = "mock"
model = None
_ml_load_error = None

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "ml",
    "recovery_model.pkl"
)

try:
    import joblib

    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        AI_ENGINE = "sklearn"

except Exception as error:
    # Covers ImportError / OSError ("DLL load failed while importing
    # _propack", Application Control blocks, missing scipy, a corrupt
    # or incompatible pickle, etc.)
    model = None
    AI_ENGINE = "mock"
    _ml_load_error = str(error)


# ---------------------------------------------------------
# Root-cause explanations, keyed by failure_reason
# ---------------------------------------------------------

ROOT_CAUSE_MAP = {
    "insufficient_funds": (
        "The customer's payment method had insufficient funds at the "
        "time of the charge. This is often temporary."
    ),
    "expired_card": (
        "The card on file has expired and needs to be updated by the "
        "customer before any retry can succeed."
    ),
    "card_declined": (
        "The card issuer declined the transaction. This may be a "
        "fraud check, a bank-side hold, or a policy decline."
    ),
    "processing_error": (
        "A transient error occurred at the payment processor. A retry "
        "is often sufficient."
    ),
    "network_error": (
        "The payment attempt failed due to a network/connectivity "
        "issue between systems rather than the card itself."
    ),
}

DEFAULT_ROOT_CAUSE = (
    "Payment failed for an unspecified or processor-level reason."
)


# ---------------------------------------------------------
# Mock AI service (deterministic, zero ML dependencies)
# ---------------------------------------------------------

def _mock_recovery_probability(features):

    score = 50.0

    if features["successful_payments"] > features["failed_payments"]:
        score += 15

    if features["subscription_active"]:
        score += 10

    if features["lifetime_value"] >= 30000:
        score += 10

    if features["retry_count"] <= 1:
        score += 10
    else:
        score -= 10 * min(features["retry_count"], 3)

    if features["failure_reason"] == "insufficient_funds":
        score += 5
    elif features["failure_reason"] in ("expired_card", "card_declined"):
        score -= 15

    if features["previous_failures"] > 2:
        score -= 10

    score = max(0, min(100, score))

    return score / 100.0


def _sklearn_recovery_probability(features):

    import pandas as pd

    features_df = pd.DataFrame([features])

    probability = model.predict_proba(features_df)[0][1]

    return float(probability)


# ---------------------------------------------------------
# Analyze payment
# ---------------------------------------------------------

def analyze_payment(payment, customer, subscription):

    features = {
        "amount": payment["amount"],
        "retry_count": payment.get("retry_count", 0),
        "successful_payments": customer["successful_payments"],
        "failed_payments": customer["failed_payments"],
        "lifetime_value": customer["lifetime_value"],
        "subscription_active": (
            1 if subscription["status"] == "active" else 0
        ),
        "previous_failures": subscription["previous_failures"],
        "failure_reason": payment.get("failure_reason")
    }

    try:
        if AI_ENGINE == "sklearn" and model is not None:
            recovery_probability = _sklearn_recovery_probability(features)
        else:
            recovery_probability = _mock_recovery_probability(features)
    except Exception:
        # Never let an AI-layer failure take down the pipeline — fall
        # back to the deterministic scorer for this single request.
        recovery_probability = _mock_recovery_probability(features)

    recovery_score = round(recovery_probability * 100)

    if recovery_score >= 75:
        recommendation = "RETRY"
        risk_level = "LOW"
    elif recovery_score >= 45:
        recommendation = "WAIT"
        risk_level = "MEDIUM"
    else:
        recommendation = "ESCALATE"
        risk_level = "HIGH"

    reasoning = []

    if customer["successful_payments"] > customer["failed_payments"]:
        reasoning.append("Customer has a strong payment history.")

    if subscription["status"] == "active":
        reasoning.append("Subscription is currently active.")

    if customer["lifetime_value"] >= 30000:
        reasoning.append("Customer has high lifetime value.")

    if features["retry_count"] <= 1:
        reasoning.append("Payment has limited previous retry attempts.")

    if features["failure_reason"] == "insufficient_funds":
        reasoning.append("Insufficient funds may be recoverable on a later attempt.")

    if features["failure_reason"] in ("expired_card", "card_declined"):
        reasoning.append("This failure reason typically requires customer action or merchant review.")

    if not reasoning:
        reasoning.append("No strong positive or negative signals found; treated as medium risk.")

    root_cause = ROOT_CAUSE_MAP.get(
        features["failure_reason"],
        DEFAULT_ROOT_CAUSE
    )

    return {
        # Kept for backward compatibility with policy_engine.py and
        # earlier frontend consumers.
        "recovery_score": recovery_score,
        "reasons": reasoning,

        # Newer, richer fields.
        "recovery_probability": round(recovery_probability, 4),
        "risk_level": risk_level,
        "root_cause": root_cause,
        "recommendation": recommendation,
        "reasoning": reasoning,
        "ai_engine": AI_ENGINE
    }