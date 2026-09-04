import os

MAX_RECOVERY_ATTEMPTS = 2
# =========================================================
# AI / ML MODEL CONFIGURATION
# =========================================================

AI_ENGINE = "mock"
model = None
_ml_load_error = None

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "ml",
    "recovery_model.pkl"
)


# =========================================================
# LOAD ML MODEL
# =========================================================

try:
    import joblib

    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        AI_ENGINE = "sklearn"

except Exception as error:
    model = None
    AI_ENGINE = "mock"
    _ml_load_error = str(error)


# =========================================================
# ROOT CAUSE MAP
# =========================================================

ROOT_CAUSE_MAP = {

    "insufficient_funds":
        "Customer account may not have sufficient funds.",

    "incorrect_otp":
        "Payment authentication failed because of an incorrect OTP.",

    "expired_card":
        "The payment card has expired.",

    "card_declined":
        "The issuing bank declined the card transaction.",

    "gateway_timeout":
        "Payment gateway or bank response timed out.",

    "authentication_failed":
        "Payment authentication failed.",

    "bank_error":
        "The customer's bank returned an error.",

    "network_error":
        "The payment could not complete because of a network or connectivity issue.",

    "upi_payment_failed":
        "The UPI payment failed during transaction processing.",

    "user_abandoned_upi_prompt":
        "The customer appears to have abandoned the UPI payment flow.",

    "payment_failed":
        "The payment was declined by the issuing bank during payment authorization.",

    "unknown":
        "The payment failure could not be classified."
}


DEFAULT_ROOT_CAUSE = (
    "The payment failure could not be classified."
)


# =========================================================
# NORMALIZATION HELPERS
# =========================================================

def _safe_int(value, default=0):
    """
    Safely convert a value to int.
    """

    try:
        return int(value)

    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    """

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


def _safe_bool(value):
    """
    Safely convert a value to boolean.
    """

    if isinstance(value, str):

        return value.strip().lower() in (
            "true",
            "1",
            "yes",
            "y",
        )

    return bool(value)


def _normalize_text(value, default="UNKNOWN"):
    """
    Normalize categorical values.
    """

    if value is None:
        return default

    value = str(value).strip()

    if not value:
        return default

    return value.upper()


# =========================================================
# RECOVERY RISK TIER
# =========================================================

def get_recovery_risk_tier(probability):
    """
    Convert recovery probability into a business risk tier.

    LOW:
        High probability of successful recovery.

    MEDIUM:
        Moderate / uncertain recovery.

    HIGH:
        Low probability of successful recovery.
    """

    probability = _safe_float(
        probability,
        0.0
    )

    # -----------------------------------------------------
    # HIGH RECOVERY POTENTIAL
    # -----------------------------------------------------

    if probability >= 0.75:

        return {
            "tier": "LOW",
            "label": "High Recovery Potential",
            "description":
                "Payment has a high probability of successful recovery.",
            "recommended_action": "RETRY"
        }

    # -----------------------------------------------------
    # MEDIUM RECOVERY POTENTIAL
    # -----------------------------------------------------

    elif probability >= 0.45:

        return {
            "tier": "MEDIUM",
            "label": "Moderate Recovery Potential",
            "description":
                "Payment has a moderate probability of successful recovery.",
            "recommended_action": "WAIT"
        }

    # -----------------------------------------------------
    # LOW RECOVERY POTENTIAL
    # -----------------------------------------------------

    else:

        return {
            "tier": "HIGH",
            "label": "Low Recovery Potential",
            "description":
                "Payment has a low probability of successful recovery.",
            "recommended_action": "ESCALATE"
        }


# =========================================================
# MOCK RECOVERY MODEL
# =========================================================

def _mock_recovery_probability(features):
    """
    Deterministic fallback recovery scorer.
    """

    score = 50.0

    successful_payments = _safe_int(
        features.get("successful_payments", 0)
    )

    failed_payments = _safe_int(
        features.get("failed_payments", 0)
    )

    subscription_active = _safe_bool(
        features.get("subscription_active", False)
    )

    lifetime_value = _safe_float(
        features.get("lifetime_value", 0)
    )

    retry_count = _safe_int(
        features.get("retry_count", 0)
    )

    previous_failures = _safe_int(
        features.get("previous_failures", 0)
    )

    failure_reason = str(
        features.get(
            "failure_reason",
            ""
        )
    ).lower()

    error_reason = str(
        features.get(
            "error_reason",
            ""
        )
    ).lower()

    # -----------------------------------------------------
    # Customer history
    # -----------------------------------------------------

    if successful_payments > failed_payments:
        score += 15

    elif failed_payments > successful_payments:
        score -= 10

    # -----------------------------------------------------
    # Subscription
    # -----------------------------------------------------

    if subscription_active:
        score += 10

    # -----------------------------------------------------
    # Customer value
    # -----------------------------------------------------

    if lifetime_value >= 30000:
        score += 10

    elif lifetime_value >= 10000:
        score += 5

    # -----------------------------------------------------
    # Retry history
    # -----------------------------------------------------

    if retry_count <= 1:
        score += 10

    else:
        score -= 10 * min(
            retry_count,
            3
        )

    # -----------------------------------------------------
    # Previous failures
    # -----------------------------------------------------

    if previous_failures > 2:
        score -= 10

    # -----------------------------------------------------
    # Failure reason
    # -----------------------------------------------------

    if failure_reason == "insufficient_funds":

        score += 5

    elif failure_reason in (
        "expired_card",
        "card_declined"
    ):

        score -= 15

    # -----------------------------------------------------
    # Razorpay error reason
    # -----------------------------------------------------

    if error_reason in (
        "incorrect_otp",
        "authentication_failed"
    ):

        score += 8

    elif error_reason in (
        "gateway_timeout",
        "network_error"
    ):

        score += 10

    elif error_reason in (
        "card_declined",
        "expired_card"
    ):

        score -= 15

    elif error_reason == "insufficient_funds":

        score += 5

    elif error_reason == "user_abandoned_upi_prompt":

        score += 12

    # -----------------------------------------------------
    # Metadata signals
    # -----------------------------------------------------

    if features.get(
        "contact_present",
        False
    ):

        score += 2

    if features.get(
        "acquirer_transaction_present",
        0
    ):

        score += 3

    session_duration = _safe_float(
        features.get(
            "cart_session_duration_seconds",
            0
        )
    )

    if session_duration >= 30:

        score += 3

    # -----------------------------------------------------
    # Clamp score
    # -----------------------------------------------------

    score = max(
        0.0,
        min(
            100.0,
            score
        )
    )

    return score / 100.0


# =========================================================
# SKLEARN MODEL
# =========================================================

def _sklearn_recovery_probability(features):
    """
    Run the metadata-based sklearn recovery model.

    The trained model expects exactly the 12 metadata
    features used during model training.
    """

    import pandas as pd

    model_features = {

        "international":
            _safe_int(
                features.get(
                    "international",
                    0
                )
            ),

        "contact_present":
            _safe_int(
                _safe_bool(
                    features.get(
                        "contact_present",
                        False
                    )
                )
            ),

        "bank":
            _normalize_text(
                features.get(
                    "bank"
                )
            ),

        "wallet":
            _normalize_text(
                features.get(
                    "wallet"
                )
            ),

        "acquirer_transaction_present":
            _safe_int(
                features.get(
                    "acquirer_transaction_present",
                    0
                )
            ),

        "error_code":
            _normalize_text(
                features.get(
                    "error_code"
                )
            ),

        "error_source":
            _normalize_text(
                features.get(
                    "error_source"
                )
            ),

        "error_step":
            _normalize_text(
                features.get(
                    "error_step"
                )
            ),

        "error_reason":
            _normalize_text(
                features.get(
                    "error_reason"
                )
            ),

        "checkout_device":
            str(
                features.get(
                    "checkout_device",
                    "UNKNOWN"
                )
            ),

        "cart_session_duration_seconds":
            _safe_float(
                features.get(
                    "cart_session_duration_seconds",
                    0
                )
            ),

        "user_preferred_language":
            str(
                features.get(
                    "user_preferred_language",
                    "UNKNOWN"
                )
            ),
    }

    features_df = pd.DataFrame(
        [model_features]
    )

    probability = model.predict_proba(
        features_df
    )[0][1]

    return float(
        probability
    )


# =========================================================
# ANALYZE PAYMENT
# =========================================================

def analyze_payment(
    payment,
    customer,
    subscription,
    ml_features=None
):
    """
    Analyze one failed payment.

    Pipeline:

        Payment
            ↓
        Customer history
            ↓
        Razorpay metadata
            ↓
        ML / deterministic scoring
            ↓
        Recovery probability
            ↓
        Risk tier
            ↓
        Recommendation
            ↓
        Root cause
            ↓
        Audit information
    """

    payment = payment or {}
    customer = customer or {}
    subscription = subscription or {}
    ml_features = ml_features or {}

    # =====================================================
    # BASIC PAYMENT FEATURES
    # =====================================================

    amount = _safe_float(
        payment.get(
            "amount",
            0
        )
    )

    retry_count = _safe_int(
        payment.get(
            "retry_count",
            0
        )
    )

    successful_payments = _safe_int(
        customer.get(
            "successful_payments",
            0
        )
    )

    failed_payments = _safe_int(
        customer.get(
            "failed_payments",
            0
        )
    )

    lifetime_value = _safe_float(
        customer.get(
            "lifetime_value",
            0
        )
    )

    previous_failures = _safe_int(
        customer.get(
            "previous_failures",
            0
        )
    )

    subscription_active = _safe_bool(
        subscription.get(
            "active",
            customer.get(
                "subscription_active",
                False
            )
        )
    )

    # =====================================================
    # FAILURE REASON
    # =====================================================

    failure_reason = (
        payment.get(
            "failure_reason"
        )
        or payment.get(
            "error_reason"
        )
        or ml_features.get(
            "error_reason"
        )
        or "unknown"
    )

    failure_reason = str(
        failure_reason
    ).lower()

    # =====================================================
    # COMBINE FEATURES
    # =====================================================

    features = {

        "amount":
            amount,

        "retry_count":
            retry_count,

        "successful_payments":
            successful_payments,

        "failed_payments":
            failed_payments,

        "lifetime_value":
            lifetime_value,

        "subscription_active":
            subscription_active,

        "previous_failures":
            previous_failures,

        "failure_reason":
            failure_reason,
    }

    # =====================================================
    # RAZORPAY METADATA FEATURES
    # =====================================================

    metadata_features = {

        "international":
            _safe_int(
                ml_features.get(
                    "international",
                    0
                )
            ),

        "contact_present":
            _safe_int(
                _safe_bool(
                    ml_features.get(
                        "contact_present",
                        False
                    )
                )
            ),

        "bank":
            _normalize_text(
                ml_features.get(
                    "bank"
                )
            ),

        "wallet":
            _normalize_text(
                ml_features.get(
                    "wallet"
                )
            ),

        "acquirer_transaction_present":
            _safe_int(
                ml_features.get(
                    "acquirer_transaction_present",
                    0
                )
            ),

        "error_code":
            _normalize_text(
                ml_features.get(
                    "error_code"
                )
            ),

        "error_source":
            _normalize_text(
                ml_features.get(
                    "error_source"
                )
            ),

        "error_step":
            _normalize_text(
                ml_features.get(
                    "error_step"
                )
            ),

        "error_reason":
            _normalize_text(
                ml_features.get(
                    "error_reason"
                )
            ),

        "checkout_device":
            str(
                ml_features.get(
                    "checkout_device",
                    "UNKNOWN"
                )
            ),

        "cart_session_duration_seconds":
            _safe_float(
                ml_features.get(
                    "cart_session_duration_seconds",
                    0
                )
            ),

        "user_preferred_language":
            str(
                ml_features.get(
                    "user_preferred_language",
                    "UNKNOWN"
                )
            ),
    }

    # =====================================================
    # ADD METADATA TO FEATURES
    # =====================================================

    features.update(
        metadata_features
    )

    # =====================================================
    # PREDICTION
    # =====================================================

    prediction_engine = AI_ENGINE

    try:

        if (
            AI_ENGINE == "sklearn"
            and model is not None
        ):

            recovery_probability = (
                _sklearn_recovery_probability(
                    features
                )
            )

        else:

            recovery_probability = (
                _mock_recovery_probability(
                    features
                )
            )

            prediction_engine = "mock"

    except Exception as error:

        print(
            "ML prediction failed; "
            "using deterministic fallback:",
            error
        )

        recovery_probability = (
            _mock_recovery_probability(
                features
            )
        )

        prediction_engine = "mock"

    # =====================================================
    # NORMALIZE PROBABILITY
    # =====================================================

    recovery_probability = max(
        0.0,
        min(
            1.0,
            float(
                recovery_probability
            )
        )
    )

    recovery_score = round(
        recovery_probability * 100
    )

    # =====================================================
    # DYNAMIC RISK TIER
    # =====================================================

    risk = get_recovery_risk_tier(
        recovery_probability
    )

    risk_level = risk["tier"]
    risk_tier = risk["tier"]
    risk_label = risk["label"]
    risk_description = risk["description"]
    recommendation = risk["recommended_action"]

    # =====================================================
    # REASONING
    # =====================================================

    reasoning = []

    # -----------------------------------------------------
    # Customer history
    # -----------------------------------------------------

    if successful_payments > failed_payments:

        reasoning.append(
            "Customer has more successful "
            "payments than failed payments."
        )

    elif failed_payments > successful_payments:

        reasoning.append(
            "Customer has a higher number "
            "of failed payments than successful payments."
        )

    # -----------------------------------------------------
    # Subscription
    # -----------------------------------------------------

    if subscription_active:

        reasoning.append(
            "Customer has an active subscription."
        )

    # -----------------------------------------------------
    # Lifetime value
    # -----------------------------------------------------

    if lifetime_value >= 30000:

        reasoning.append(
            "Customer has high lifetime value."
        )

    elif lifetime_value >= 10000:

        reasoning.append(
            "Customer has meaningful lifetime value."
        )

    # -----------------------------------------------------
    # Retry history
    # -----------------------------------------------------

    if retry_count <= 1:

        reasoning.append(
            "Payment has limited previous retry attempts."
        )

    else:

        reasoning.append(
            f"Payment has already been retried "
            f"{retry_count} time(s)."
        )

    # =====================================================
    # RAZORPAY ERROR-AWARE REASONING
    # =====================================================

    error_code = metadata_features[
        "error_code"
    ]

    error_source = metadata_features[
        "error_source"
    ]

    error_step = metadata_features[
        "error_step"
    ]

    error_reason = metadata_features[
        "error_reason"
    ]

    if error_code != "UNKNOWN":

        reasoning.append(
            f"Razorpay error code: "
            f"{error_code}."
        )

    if error_source != "UNKNOWN":

        reasoning.append(
            f"Payment failure originated "
            f"from {error_source}."
        )

    if error_step != "UNKNOWN":

        reasoning.append(
            f"Failure occurred during "
            f"{error_step}."
        )

    if error_reason != "UNKNOWN":

        reasoning.append(
            f"Razorpay failure reason: "
            f"{error_reason}."
        )

    # =====================================================
    # FAILURE-SPECIFIC REASONING
    # =====================================================

    if failure_reason == "insufficient_funds":

        reasoning.append(
            "Insufficient funds may be recoverable "
            "on a later attempt."
        )

    elif failure_reason in (
        "expired_card",
        "card_declined"
    ):

        reasoning.append(
            "This failure reason typically requires "
            "customer action or merchant review."
        )

    elif failure_reason == "incorrect_otp":

        reasoning.append(
            "Customer authentication failed; "
            "a controlled retry may be appropriate."
        )

    elif failure_reason == "gateway_timeout":

        reasoning.append(
            "A temporary gateway or bank timeout "
            "may be recoverable through a controlled retry."
        )

    elif failure_reason == "user_abandoned_upi_prompt":

        reasoning.append(
            "The customer appears to have abandoned "
            "the UPI payment flow; targeted recovery "
            "communication may be appropriate."
        )

    # =====================================================
    # METADATA REASONING
    # =====================================================

    if metadata_features[
        "contact_present"
    ]:

        reasoning.append(
            "Customer contact information is available "
            "for an approved recovery workflow."
        )

    if metadata_features[
        "acquirer_transaction_present"
    ]:

        reasoning.append(
            "Acquirer transaction information is available."
        )

    checkout_device = metadata_features[
        "checkout_device"
    ]

    if checkout_device != "UNKNOWN":

        reasoning.append(
            f"Checkout device: "
            f"{checkout_device}."
        )

    preferred_language = metadata_features[
        "user_preferred_language"
    ]

    if preferred_language != "UNKNOWN":

        reasoning.append(
            f"Preferred language: "
            f"{preferred_language}."
        )

    session_duration = metadata_features[
        "cart_session_duration_seconds"
    ]

    if session_duration > 0:

        reasoning.append(
            f"Checkout session duration: "
            f"{session_duration:.0f} seconds."
        )

    # =====================================================
    # FALLBACK REASON
    # =====================================================

    if not reasoning:

        reasoning.append(
            "No strong positive or negative signals "
            "were found; payment treated as medium risk."
        )

    # =====================================================
    # ROOT CAUSE
    # =====================================================

    root_cause = ROOT_CAUSE_MAP.get(
        failure_reason,
        DEFAULT_ROOT_CAUSE
    )

    # =====================================================
# STOP-RULE INFORMATION
# =====================================================

    if retry_count >= MAX_RECOVERY_ATTEMPTS:

     stop_rule = {
        "triggered": True,
        "rule": "Maximum recovery attempts reached.",
        "action": "Automated retry blocked; escalate."
    }

    # Override recommendation because
    # the policy boundary has been reached.

     recommendation = "ESCALATE"

    elif retry_count >= MAX_RECOVERY_ATTEMPTS - 1:

      stop_rule = {
        "triggered": True,
        "rule": "Retry threshold approaching limit.",
        "action": "Do not perform repeated automated retries."
    }

    else:

      stop_rule = {
        "triggered": False,
        "rule": "Retry threshold not reached.",
        "action": "Normal recovery policy evaluation allowed."
    }

    # =====================================================
    # OPERATIONAL DECISION
    # =====================================================

    if recommendation == "RETRY":

        operational_action = {
            "type": "AUTOMATED_RETRY",
            "allowed": True,
            "description":
                "Controlled payment retry is permitted."
        }

    elif recommendation == "WAIT":

        operational_action = {
            "type": "WAIT",
            "allowed": False,
            "description":
                "Delay recovery and reassess before another attempt."
        }

    else:

        operational_action = {
            "type": "ESCALATION",
            "allowed": False,
            "description":
                "Automated recovery stopped; manual review required."
        }

    # =====================================================
    # RETURN ANALYSIS
    # =====================================================

    return {

        # -------------------------------------------------
        # Core decision
        # -------------------------------------------------

        "recovery_score":
            recovery_score,

        "recovery_probability":
            round(
                recovery_probability,
                4
            ),

        "risk_level":
            risk_level,

        "risk_tier":
            risk_tier,

        "risk_label":
            risk_label,

        "risk_description":
            risk_description,

        "recommendation":
            recommendation,

        # -------------------------------------------------
        # Explanation
        # -------------------------------------------------

        "root_cause":
            root_cause,

        "reasons":
            reasoning,

        "reasoning":
            reasoning,

        # -------------------------------------------------
        # Engine
        # -------------------------------------------------

        "ai_engine":
            prediction_engine,

        # -------------------------------------------------
        # ML inputs / audit
        # -------------------------------------------------

        "ml_features":
            metadata_features,

        # -------------------------------------------------
        # Stop rule
        # -------------------------------------------------

        "stop_rule":
            stop_rule,

        # -------------------------------------------------
        # Operational action
        # -------------------------------------------------

        "operational_action":
            operational_action,

        # -------------------------------------------------
        # Debug information
        # -------------------------------------------------

        "ml_model_loaded":
            model is not None,

        "ml_model_path":
            MODEL_PATH,

        "ml_load_error":
            _ml_load_error,
    }