def evaluate_policy(payment, analysis):

    recovery_score = analysis["recovery_score"]
    recommendation = analysis["recommendation"]

    failure_reason = payment.get("failure_reason")

    # Payment methods that normally require customer intervention
    high_risk_reasons = [
        "expired_card",
        "card_declined"
    ]

    # Never automatically retry these
    if failure_reason in high_risk_reasons:

        return {
            "action": "RETRY_WITH_APPROVAL",
            "requires_merchant_approval": True,
            "reason": (
                f"Failure reason '{failure_reason}' requires "
                "additional review before retry."
            )
        }

    # High-confidence recoverable payment
    if recovery_score >= 80 and recommendation == "RETRY":

        return {
            "action": "AUTO_RETRY",
            "requires_merchant_approval": False,
            "reason": "High probability of successful recovery."
        }

    # Medium confidence
    elif recovery_score >= 60 and recommendation == "RETRY":

        return {
            "action": "RETRY_WITH_APPROVAL",
            "requires_merchant_approval": True,
            "reason": "Recovery is possible, but merchant approval is required."
        }

    # Low confidence
    else:

        return {
            "action": "DO_NOT_RETRY",
            "requires_merchant_approval": True,
            "reason": "Recovery probability is too low for automatic retry."
        }