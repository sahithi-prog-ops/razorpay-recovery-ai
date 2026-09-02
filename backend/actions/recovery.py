from state_manager import (
    save_payment_state,
    add_audit_event,
    get_payment_state,
    create_escalation
)


# =========================================================
# BOUNDED RECOVERY CONFIGURATION
# =========================================================

MAX_RECOVERY_ATTEMPTS = 2


# Terminal states mean the agent must stop.
TERMINAL_STATES = {
    "recovered",
    "rejected",
    "escalated",
    "blocked"
}


# =========================================================
# VERIFICATION
# =========================================================

def verify_recovery(
    payment_id,
    expected_amount
):

    record = get_payment_state(
        payment_id
    )

    if not record:

        return {

            "verified":
                False,

            "message":
                "Payment state not found.",

            "checks": {

                "action_is_retry_payment":
                    False,

                "amount_recorded":
                    False,

                "processor_confirmed":
                    False,

                "amount_matches_expected":
                    False
            }
        }

    action = record.get(
        "action"
    )

    recorded_amount = record.get(
        "recovered_amount"
    )

    processor_confirmed = record.get(
        "processor_confirmed",
        False
    )

    action_ok = (
        action == "AUTO_RETRY"
        or
        action == "RETRY_WITH_APPROVAL"
        or
        action == "RECOVERY_EXECUTED"
    )

    amount_recorded = (
        recorded_amount is not None
    )

    amount_matches = (
        amount_recorded
        and
        float(recorded_amount)
        == float(expected_amount)
    )

    verified = (
        action_ok
        and
        amount_recorded
        and
        processor_confirmed
        and
        amount_matches
    )

    return {

        "verified":
            verified,

        "message":
            (
                "Recovery verified successfully."
                if verified
                else
                "Recovery verification failed."
            ),

        "checks": {

            "action_is_retry_payment":
                action_ok,

            "amount_recorded":
                amount_recorded,

            "processor_confirmed":
                processor_confirmed,

            "amount_matches_expected":
                amount_matches
        }
    }

def execute_recovery(
    payment_id,
    amount,
    trigger="AUTO_RETRY"
):

    record = get_payment_state(
        payment_id
    )

    if not record:

        raise ValueError(
            "Payment not found."
        )

    current_status = record.get(
        "status"
    )

    # =====================================================
    # TERMINAL STATE GUARD
    # =====================================================

    if current_status in TERMINAL_STATES:

        add_audit_event(

            payment_id,

            "RECOVERY_BLOCKED_TERMINAL_STATE",

            {
                "status":
                    current_status,

                "reason":
                    "No further automated recovery actions allowed."
            }
        )

        return (
            False,
            record.get("verification"),
            None
        )

    # =====================================================
    # ATTEMPT LIMIT
    # =====================================================

    retry_count = int(
        record.get(
            "retry_count",
            0
        )
    )

    if retry_count >= MAX_RECOVERY_ATTEMPTS:

        escalation = create_escalation(

            payment_id,

            reason=
                "Maximum recovery attempts reached.",

            severity=
                "high",

            recommended_action=
                "Manual merchant review."
        )

        verification = {

            "verified":
                False,

            "payment_id":
                payment_id,

            "status":
                "verification_failed",

            "message":
                "Maximum recovery attempts reached.",

            "checks": {

                "action_is_retry_payment":
                    False,

                "amount_recorded":
                    False,

                "processor_confirmed":
                    False,

                "amount_matches_expected":
                    False
            }
        }

        save_payment_state(

            payment_id,

            status=
                "escalated",

            action=
                "RECOVERY_STOPPED",

            verification=
                verification
        )

        add_audit_event(

            payment_id,

            "BOUNDED_ACTION_STOP",

            {

                "retry_count":
                    retry_count,

                "max_attempts":
                    MAX_RECOVERY_ATTEMPTS,

                "reason":
                    "Recovery attempt limit reached."
            }
        )

        return (
            False,
            verification,
            escalation
        )

    # =====================================================
    # RECORD ATTEMPT
    # =====================================================

    attempt_number = (
        retry_count + 1
    )

    add_audit_event(

        payment_id,

        "RECOVERY_ATTEMPT_STARTED",

        {

            "attempt":
                attempt_number,

            "max_attempts":
                MAX_RECOVERY_ATTEMPTS,

            "trigger":
                trigger
        }
    )

    # =====================================================
    # SIMULATED PROCESSOR RESULT
    # =====================================================

    processor_confirmed = True

    # =====================================================
    # SAVE EXECUTION RESULT
    # =====================================================

    save_payment_state(

        payment_id,

        retry_count=
            attempt_number,

        action=
            "RECOVERY_EXECUTED",

        recovered_amount=
            amount,

        processor_confirmed=
            processor_confirmed
    )

    add_audit_event(

        payment_id,

        "RECOVERY_ACTION_EXECUTED",

        {

            "attempt":
                attempt_number,

            "amount":
                amount,

            "processor_confirmed":
                processor_confirmed,

            "bounded":
                True,

            "max_attempts":
                MAX_RECOVERY_ATTEMPTS
        }
    )

    # =====================================================
    # VERIFY
    # =====================================================

    verification = verify_recovery(

        payment_id,

        amount
    )

    save_payment_state(

        payment_id,

        verification=
            verification
    )

    add_audit_event(

        payment_id,

        "RECOVERY_VERIFICATION",

        verification
    )

    # =====================================================
    # SUCCESS
    # =====================================================

    if verification["verified"]:

        save_payment_state(

            payment_id,

            status=
                "recovered",

            action=
                "RECOVERY_EXECUTED",

            recovery_lock=
                False,

            recovery_lock_status=
                "COMPLETED"
        )

        add_audit_event(

            payment_id,

            "PAYMENT_RECOVERED",

            {

                "amount":
                    amount,

                "attempt":
                    attempt_number,

                "verified":
                    True
            }
        )

        return (
            True,
            verification,
            None
        )

    # =====================================================
    # VERIFICATION FAILURE
    # =====================================================

    escalation = create_escalation(

        payment_id,

        reason=
            "Recovery execution could not be verified.",

        severity=
            "high",

        recommended_action=
            "Manual review required."
    )

    save_payment_state(

        payment_id,

        status=
            "escalated",

        recovery_lock=
            False,

        recovery_lock_status=
            "ESCALATED"
    )

    add_audit_event(

        payment_id,

        "RECOVERY_ESCALATED_AFTER_VERIFICATION_FAILURE",

        escalation
    )

    return (
        False,
        verification,
        escalation
    )
# =========================================================
# APPROVE
# =========================================================

def approve_recovery(
    payment_id
):

    record = get_payment_state(
        payment_id
    )

    if not record:

        raise ValueError(
            "Payment not found."
        )

    status = record.get(
        "status"
    )

    if status != "pending_approval":

        raise ValueError(
            f"Payment is not awaiting approval. Current status: {status}"
        )

    add_audit_event(

        payment_id,

        "MERCHANT_APPROVAL_GRANTED",

        {

            "previous_status":
                status
        }
    )

    amount = record.get(
        "amount",
        0
    )

    result = execute_recovery(

        payment_id,

        amount,

        trigger=
            "MERCHANT_APPROVAL"
    )

    return {

        "status":
            "processed",

        "payment_id":
            payment_id,

        "verification":
            result[1],

        "escalation":
            result[2],

        "payment_status":
            get_payment_state(
                payment_id
            ).get("status")
    }


# =========================================================
# REJECT
# =========================================================

def reject_recovery(
    payment_id
):

    record = get_payment_state(
        payment_id
    )

    if not record:

        raise ValueError(
            "Payment not found."
        )

    if record.get("status") != "pending_approval":

        raise ValueError(
            "Payment is not awaiting approval."
        )

    save_payment_state(

        payment_id,

        status=
            "rejected",

        action=
            "RECOVERY_REJECTED"
    )

    add_audit_event(

        payment_id,

        "MERCHANT_APPROVAL_REJECTED",

        {

            "action":
                "RECOVERY_REJECTED"
        }
    )

    return {

        "status":
            "rejected",

        "payment_id":
            payment_id
    }