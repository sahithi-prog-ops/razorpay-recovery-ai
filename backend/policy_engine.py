# =========================================================
# RECOVERY POLICY ENGINE
# =========================================================

# Minimum probability for automatic recovery.
# =========================================================
# RECOVERY POLICY ENGINE
# =========================================================

AUTO_RETRY_THRESHOLD = 0.75
APPROVAL_THRESHOLD = 0.45

MAX_RECOVERY_ATTEMPTS = 2


def _probability(analysis):

    probability = analysis.get(
        "recovery_probability",
        0
    )

    try:
        return float(probability)
    except (TypeError, ValueError):
        return 0.0


def evaluate_policy(payment, analysis):

    probability = _probability(
        analysis
    )

    retry_count = payment.get(
        "retry_count",
        0
    )

    failure_reason = (
        payment.get(
            "failure_reason"
        )
        or "unknown"
    )

    risk_tier = analysis.get(
        "risk_tier",
        "HIGH"
    )

    risk_label = analysis.get(
        "risk_label",
        "Low Recovery Potential"
    )

    # =====================================================
    # HARD SAFETY GUARD
    # =====================================================

    if retry_count >= MAX_RECOVERY_ATTEMPTS:

        return {
            "action": "DO_NOT_RETRY",

            "requires_merchant_approval": False,

            "reason":
                "Recovery attempt limit reached.",

            "guardrail":
                "MAX_ATTEMPTS_REACHED",

            "probability":
                probability,

            "risk_tier":
                risk_tier,

            "risk_label":
                risk_label,

            "failure_reason":
                failure_reason,

            "max_attempts":
                MAX_RECOVERY_ATTEMPTS
        }

    # =====================================================
    # HIGH RECOVERY POTENTIAL
    # =====================================================

    if probability >= AUTO_RETRY_THRESHOLD:

        return {
            "action":
                "AUTO_RETRY",

            "requires_merchant_approval":
                False,

            "reason":
                "High probability of successful recovery.",

            "guardrail":
                "AUTO_RETRY_ALLOWED",

            "probability":
                probability,

            "risk_tier":
                risk_tier,

            "risk_label":
                risk_label,

            "failure_reason":
                failure_reason,

            "max_attempts":
                MAX_RECOVERY_ATTEMPTS
        }

    # =====================================================
    # MEDIUM RECOVERY POTENTIAL
    # =====================================================

    if probability >= APPROVAL_THRESHOLD:

        return {
            "action":
                "RETRY_WITH_APPROVAL",

            "requires_merchant_approval":
                True,

            "reason":
                "Recovery probability is moderate; merchant approval is required before retry.",

            "guardrail":
                "MERCHANT_APPROVAL_REQUIRED",

            "probability":
                probability,

            "risk_tier":
                risk_tier,

            "risk_label":
                risk_label,

            "failure_reason":
                failure_reason,

            "max_attempts":
                MAX_RECOVERY_ATTEMPTS
        }

    # =====================================================
    # LOW RECOVERY POTENTIAL
    # =====================================================

    return {
        "action":
            "DO_NOT_RETRY",

        "requires_merchant_approval":
            False,

        "reason":
            "Recovery probability is below the safe intervention threshold.",

        "guardrail":
            "LOW_PROBABILITY",

        "probability":
            probability,

        "risk_tier":
            risk_tier,

        "risk_label":
            risk_label,

        "failure_reason":
            failure_reason,

        "max_attempts":
            MAX_RECOVERY_ATTEMPTS
    }