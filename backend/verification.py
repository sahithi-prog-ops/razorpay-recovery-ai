import hashlib

from backend.state_manager import (
    get_payment_state,
    save_payment_state,
    add_audit_event,
)


def _simulate_processor_confirmation(payment_id, amount):
    """
    Deterministic stand-in for calling out to a payment processor to
    confirm a retried charge actually went through. NO real network
    call or financial transaction is made.

    - Any payment_id containing "failverify" always fails verification,
      so the escalation path can be demoed reliably on demand.
    - Otherwise, the outcome is deterministic per (payment_id, amount)
      — same inputs always produce the same result — and succeeds
      about 95% of the time, so most demo runs recover cleanly while
      the failure path still exists and is testable.
    """

    if "failverify" in payment_id.lower():
        return False

    seed = int(hashlib.sha256(f"{payment_id}:{amount}".encode()).hexdigest(), 16)

    return seed % 20 != 0


def verify_recovery(
    payment_id,
    expected_amount=None,
    expected_action="RETRY_PAYMENT"
):
    """
    Simulated post-recovery verification. NO real financial calls are
    made — this checks the internal state that actions/recovery.py
    just wrote (that a retry action was recorded, that an amount is
    present) plus a deterministic simulated processor confirmation,
    then stores and logs the result.

    Importantly, this function does NOT set payment status to
    "recovered" itself — the caller (actions/recovery.py) only marks a
    payment "recovered" once verified is True here. That's what
    guarantees recovered_revenue in /metrics only ever includes
    verified recoveries.

    Returns:
        {
            "verified": true,
            "payment_id": "...",
            "amount": ...,
            "status": "recovered",
            "message": "Recovery verified successfully.",
            "checks": {...}
        }

    or, on failure:
        {
            "verified": false,
            "payment_id": "...",
            "amount": ...,
            "status": "verification_failed",
            "message": "Recovery verification failed: <reason>.",
            "checks": {...}
        }
    """

    record = get_payment_state(payment_id)

    if not record:
        result = {
            "verified": False,
            "payment_id": payment_id,
            "amount": expected_amount,
            "status": "unknown",
            "message": "Recovery verification failed: payment not found.",
            "checks": {}
        }

        add_audit_event(payment_id, "VERIFICATION_COMPLETE", result)

        return result

    actual_action = record.get("action")
    actual_amount = record.get("amount", 0) or 0

    amount_for_processor_check = (
        expected_amount if expected_amount is not None else actual_amount
    )

    checks = {
        "action_is_retry_payment": actual_action == expected_action,
        "amount_recorded": bool(actual_amount),
        "processor_confirmed": _simulate_processor_confirmation(
            payment_id, amount_for_processor_check
        ),
    }

    if expected_amount is not None:
        checks["amount_matches_expected"] = actual_amount == expected_amount

    verified = all(checks.values())

    if verified:
        message = "Recovery verified successfully."
    else:
        failed_checks = [name for name, passed in checks.items() if not passed]
        message = f"Recovery verification failed: {', '.join(failed_checks)}."

    result = {
        "verified": verified,
        "payment_id": payment_id,
        "amount": actual_amount,
        "status": "recovered" if verified else "verification_failed",
        "message": message,
        "checks": checks
    }

    save_payment_state(payment_id, verification=result)

    add_audit_event(payment_id, "VERIFICATION_COMPLETE", result)

    if verified:
        add_audit_event(payment_id, "RECOVERY_VERIFIED", result)

    return result