# =========================================================
# RECOVERY POLICY ENGINE
# =========================================================

# Minimum probability for automatic recovery.
AUTO_RETRY_THRESHOLD = 0.80

# Minimum probability where merchant approval can be useful.
APPROVAL_THRESHOLD = 0.40

# Maximum number of recovery attempts allowed.
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


def evaluate_policy(
    payment,
    analysis
):

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

    # =====================================================
    # HARD SAFETY GUARD
    # =====================================================

    if retry_count >= MAX_RECOVERY_ATTEMPTS:

        return {

            "action":
                "DO_NOT_RETRY",

            "requires_merchant_approval":
                False,

            "reason":
                "Recovery attempt limit reached.",

            "guardrail":
                "MAX_RETRY_LIMIT",

            "max_attempts":
                MAX_RECOVERY_ATTEMPTS,

            "current_attempt":
                retry_count
        }

    # =====================================================
    # VERY LOW PROBABILITY
    # =====================================================

    if probability < APPROVAL_THRESHOLD:

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

            "failure_reason":
                failure_reason
        }

    # =====================================================
    # HIGH PROBABILITY
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

            "failure_reason":
                failure_reason,

            "max_attempts":
                MAX_RECOVERY_ATTEMPTS
        }

    # =====================================================
    # MEDIUM PROBABILITY
    # =====================================================

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

        "failure_reason":
            failure_reason,

        "max_attempts":
            MAX_RECOVERY_ATTEMPTS
    }