from backend.state_manager import (
    save_payment_state,
    add_audit_event,
    get_payment_state,
    create_escalation
)

from backend.razorpay_service import verify_payment


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

    result = execute_approved_recovery(

        payment_id,

        amount
    )

    return {

        "status":
            result.get(
                "status",
                "processed"
            ),

        "payment_id":
            payment_id,

        "verification":
            result.get(
                "verification"
            ),

        "escalation":
            result.get(
                "escalation"
            ),

        "payment_status":
            get_payment_state(
                payment_id
            ).get(
                "status"
            )
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



# =========================================================
# APPROVED RECOVERY EXECUTION
# =========================================================
# =========================================================
# APPROVED RECOVERY EXECUTION
# =========================================================
# =========================================================
# APPROVED RECOVERY EXECUTION
# =========================================================

def execute_approved_recovery(
    payment_id,
    amount
):
    """
    Execute a retry after explicit merchant approval.

    Recovery is NOT marked as recovered until
    the processor confirms the payment.
    """

    # =====================================================
    # GET PAYMENT STATE
    # =====================================================

    record = get_payment_state(
        payment_id
    )

    if not record:

        raise ValueError(
            "Payment not found."
        )

    retry_count = int(
        record.get(
            "retry_count",
            0
        )
    )

    # =====================================================
    # TERMINAL STATE GUARD
    # =====================================================

    current_status = record.get(
        "status"
    )

    if current_status in TERMINAL_STATES:

        add_audit_event(

            payment_id,

            "RECOVERY_BLOCKED_TERMINAL_STATE",

            {

                "status":
                    current_status,

                "reason":
                    "No further recovery actions allowed."
            }
        )

        return {

            "status":
                "BLOCKED",

            "executed":
                False,

            "action":
                "RECOVERY_BLOCKED",

            "payment_id":
                payment_id,

            "retry_count":
                retry_count
        }

    # =====================================================
    # MAX ATTEMPTS GUARD
    # =====================================================

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

        save_payment_state(

            payment_id,

            status=
                "escalated",

            action=
                "RECOVERY_STOPPED",

            recovery_lock=
                False,

            recovery_lock_status=
                "ESCALATED",

            processor_confirmed=
                False
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

        return {

            "status":
                "ESCALATED",

            "executed":
                False,

            "action":
                "RECOVERY_STOPPED",

            "payment_id":
                payment_id,

            "retry_count":
                retry_count,

            "escalation":
                escalation
        }

    # =====================================================
    # ATTEMPT NUMBER
    # =====================================================

    attempt_number = (
        retry_count + 1
    )

    add_audit_event(

        payment_id,

        "APPROVED_RECOVERY_ATTEMPT_STARTED",

        {

            "attempt":
                attempt_number,

            "max_attempts":
                MAX_RECOVERY_ATTEMPTS,

            "trigger":
                "MERCHANT_APPROVAL"
        }
    )

    # =====================================================
    # RECORD EXECUTION ATTEMPT
    # =====================================================

    # =====================================================
# RECOVERY EXECUTION
# =====================================================

# The recovery attempt has been initiated,
# but it is NOT considered recovered yet.
    processor_confirmed = False

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
    # REAL RAZORPAY PROCESSOR VERIFICATION
    # =====================================================

    processor_verification = verify_payment(

        payment_id,

        int(amount)
    )

    # =====================================================
    # SAVE PROCESSOR VERIFICATION
    # =====================================================

    processor_confirmed = bool(
        processor_verification.get(
            "verified",
            False
        )
    )

    save_payment_state(

        payment_id,

        processor_verification=
            processor_verification,

        processor_confirmed=
            processor_confirmed
    )

    add_audit_event(

        payment_id,

        "PROCESSOR_VERIFICATION",

        {

            "attempt":
                attempt_number,

            "processor_confirmed":
                processor_confirmed,

            "verification":
                processor_verification
        }
    )

    # =====================================================
    # SUCCESS
    # =====================================================

    if processor_confirmed:

        verification = {

            "verified":
                True,

            "payment_id":
                payment_id,

            "processor_confirmed":
                True,

            "amount_matches_expected":
                processor_verification.get(
                    "amount_matches",
                    False
                ),

            "checks": {

                "action_is_retry_payment":
                    True,

                "amount_recorded":
                    True,

                "processor_confirmed":
                    True,

                "amount_matches_expected":
                    processor_verification.get(
                        "amount_matches",
                        False
                    )
            }
        }

        save_payment_state(

            payment_id,

            status=
                "recovered",

            action=
                "RECOVERY_EXECUTED",

            recovery_lock=
                False,

            recovery_lock_status=
                "COMPLETED",

            processor_confirmed=
                True,

            verification=
                verification
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
                    True,

                "processor_confirmed":
                    True
            }
        )

        return {

            "status":
                "RECOVERED",

            "executed":
                True,

            "action":
                "RECOVERY_EXECUTED",

            "payment_id":
                payment_id,

            "retry_count":
                attempt_number,

            "amount":
                amount,

            "verification":
                verification,

            "processor_verification":
                processor_verification
        }

    # =====================================================
    # VERIFICATION FAILED
    # =====================================================

    verification = {

        "verified":
            False,

        "payment_id":
            payment_id,

        "processor_confirmed":
            False,

        "message":
            "Razorpay processor verification failed.",

        "processor_verification":
            processor_verification
    }

    save_payment_state(

        payment_id,

        status=
            "escalated",

        action=
            "RECOVERY_EXECUTED",

        recovery_lock=
            False,

        recovery_lock_status=
            "ESCALATED",

        processor_confirmed=
            False,

        verification=
            verification
    )

    escalation = create_escalation(

        payment_id,

        reason=
            "Approved recovery could not be verified by Razorpay.",

        severity=
            "high",

        recommended_action=
            "Manual review required."
    )

    add_audit_event(

        payment_id,

        "RECOVERY_VERIFICATION_FAILED",

        {

            "amount":
                amount,

            "attempt":
                attempt_number,

            "verified":
                False,

            "processor_confirmed":
                False,

            "processor_verification":
                processor_verification
        }
    )

    return {

        "status":
            "ESCALATED",

        "executed":
            False,

        "action":
            "RECOVERY_EXECUTED",

        "payment_id":
            payment_id,

        "retry_count":
            attempt_number,

        "verification":
            verification,

        "processor_verification":
            processor_verification,

        "escalation":
            escalation
    }

       

