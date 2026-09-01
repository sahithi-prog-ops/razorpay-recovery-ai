from state_manager import (
    get_payment_state,
    save_payment_state,
    add_audit_event,
    create_escalation
)

from verification import verify_recovery


# A payment in any of these states has already been fully resolved.
# Nothing in this module will ever act on a payment in one of these
# states — this is the single source of truth for "is this payment
# done".
TERMINAL_STATES = ("recovered", "rejected", "escalated")


def execute_recovery(payment_id, amount, trigger="AUTO_RETRY"):
    """
    Attempts the simulated recovery action (a retried charge) and then
    runs verification. NO real financial transaction is performed.

    Revenue is only counted as recovered once verification succeeds:
      - if verified, the payment is marked "recovered".
      - if verification fails, the payment is escalated automatically
        (status -> "escalated") instead of ever being marked
        recovered.

    Returns (updated_record, verification_result, escalation_or_None).
    """

    save_payment_state(
        payment_id,
        action="RETRY_PAYMENT",
        amount=amount
    )

    add_audit_event(
        payment_id,
        "RECOVERY_ACTION",
        {
            "action": "RETRY_PAYMENT",
            "trigger": trigger,
            "amount": amount,
            "simulated": True
        }
    )

    verification = verify_recovery(payment_id, expected_amount=amount)

    if verification["verified"]:

        updated = save_payment_state(
            payment_id,
            status="recovered",
            amount=amount
        )

        return updated, verification, None

    # Verification failed — escalate automatically. The payment is
    # NEVER marked "recovered" in this branch, so /metrics can never
    # count this revenue as recovered.
    escalation = create_escalation(
        payment_id,
        reason="Automated recovery attempt failed verification.",
        severity="high",
        recommended_action="Manual merchant review and retry required."
    )

    updated = save_payment_state(
        payment_id,
        status="escalated"
    )

    add_audit_event(payment_id, "ESCALATION_CREATED", escalation)

    return updated, verification, escalation


def approve_recovery(payment_id):
    """
    Merchant approval -> simulated recovery execution -> verification.

    Only allowed when the payment is currently "pending_approval".
    Refuses (safely) for any other state, including every terminal
    state, so recovery can never be executed twice.
    """

    record = get_payment_state(payment_id)

    if not record:
        return {
            "payment_id": payment_id,
            "approval": "error",
            "message": "Payment not found.",
            "recovery": None,
            "verification": None,
            "escalation": None
        }

    current_status = record.get("status")

    if current_status != "pending_approval":
        return {
            "payment_id": payment_id,
            "approval": "blocked",
            "message": (
                f"Payment is not pending approval (current status: "
                f"'{current_status}'). No action taken."
            ),
            "recovery": record,
            "verification": record.get("verification"),
            "escalation": None
        }

    add_audit_event(
        payment_id,
        "RECOVERY_APPROVED",
        {"previous_status": current_status}
    )

    amount = record.get("amount", 0)

    updated, verification, escalation = execute_recovery(
        payment_id, amount, trigger="MERCHANT_APPROVED"
    )

    if escalation:
        message = "Recovery attempt failed verification and was escalated for manual review."
    else:
        message = "Recovery executed and verified successfully."

    return {
        "payment_id": payment_id,
        "approval": "approved",
        "message": message,
        "recovery": updated,
        "verification": verification,
        "escalation": escalation
    }


def reject_recovery(payment_id):
    """
    Merchant rejection. Only allowed when the payment is currently
    "pending_approval".
    """

    record = get_payment_state(payment_id)

    if not record:
        return {
            "payment_id": payment_id,
            "rejection": "error",
            "message": "Payment not found.",
            "recovery": None
        }

    current_status = record.get("status")

    if current_status != "pending_approval":
        return {
            "payment_id": payment_id,
            "rejection": "blocked",
            "message": (
                f"Payment is not pending approval (current status: "
                f"'{current_status}'). No action taken."
            ),
            "recovery": record
        }

    updated = save_payment_state(
        payment_id,
        status="rejected",
        action="NO_ACTION"
    )

    add_audit_event(
        payment_id,
        "RECOVERY_REJECTED",
        {"previous_status": current_status}
    )

    return {
        "payment_id": payment_id,
        "rejection": "rejected",
        "message": "Recovery rejected by merchant. No action taken.",
        "recovery": updated
    }