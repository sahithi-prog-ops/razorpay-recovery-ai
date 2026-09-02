
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env explicitly from the backend folder
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Razorpay public API key
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from razorpay_service import (
    verify_webhook_signature,
    create_recovery_order,
    verify_checkout_signature,
    verify_payment,
)

from planner import create_plan

from analyzer import (
    analyze_payment
)

from policy_engine import (
    evaluate_policy
)

from actions.recovery import (
    approve_recovery,
    reject_recovery,
    execute_recovery,
    TERMINAL_STATES
)

from metrics import (
    calculate_metrics
)

from state_manager import (
    save_payment_state,
    add_audit_event,
    get_audit_log,
    get_payment_state,
    get_all_payment_states,
    create_escalation,
    get_escalations_for_payment,
    reserve_payment
)

app = FastAPI(
    title="RecoverAI"
)#======================================
# CORS
# =========================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# HEALTH
# =========================================================

@app.get("/")
def root():

    return {

        "status":
            "ok",

        "service":
            "RecoverAI",

        "safety_features": [

            "Idempotent Webhook Processing",

            "Bounded Recovery Actions",

            "Post-Recovery Verification",

            "Immutable Audit Events"
        ],

        "pipeline": [

            "Webhook",

            "Payment Validation",

            "Idempotency Guard",

            "Risk / Detection",

            "AI Analysis",

            "Policy Engine",

            "Bounded Recovery Action",

            "Verification",

            "Recovered Revenue",

            "Audit Log",

            "Metrics / Dashboard"
        ]
    }

# =========================================================
# PAYMENTS LIST
# =========================================================

@app.get("/payments")
def list_payments():

    states = get_all_payment_states()

    payments = []

    for payment_id, record in states.items():

        # -------------------------------------------------
        # 1. Prefer stored AI analysis
        # -------------------------------------------------

        stored_analysis = record.get("analysis") or {}

        recovery_score = stored_analysis.get("recovery_score")

        # -------------------------------------------------
        # 2. If missing, calculate using the SAME planner
        #    and analyzer used by /plan/{payment_id}
        # -------------------------------------------------

        if recovery_score is None:

            try:

                plan = create_plan(payment_id)

                if plan:

                    analysis = analyze_payment(
                        plan["payment"],
                        plan["customer"],
                        plan["subscription"]
                    )

                    recovery_score = analysis.get(
                        "recovery_score"
                    )

                    # -----------------------------------------
                    # Store the calculated analysis so future
                    # dashboard requests don't need to
                    # recalculate it.
                    # -----------------------------------------

                    if recovery_score is not None:

                        save_payment_state(
                            payment_id,
                            analysis=analysis
                        )

                else:

                    recovery_score = 0

            except Exception as error:

                print(
                    f"AI analysis failed for {payment_id}: {error}"
                )

                recovery_score = 0

        # -------------------------------------------------
        # 3. Safety fallback
        # -------------------------------------------------

        if recovery_score is None:
            recovery_score = 0

        # -------------------------------------------------
        # 4. Dashboard response
        # -------------------------------------------------

        payments.append({

            "payment_id":
                payment_id,

            "customer_id":
                record.get("customer_id"),

            "amount":
                record.get("amount", 0),

            "failure_reason":
                record.get("failure_reason"),

            "recovery_probability":
                recovery_score,

            "status":
                record.get("status")
        })

    return {
        "payments": payments
    }
# =========================================================
# PENDING
# =========================================================

@app.get("/pending")
def list_pending():

    states = get_all_payment_states()

    pending = [

        {

            "payment_id":
                payment_id,

            "customer_id":
                record.get(
                    "customer_id"
                ),

            "amount":
                record.get(
                    "amount",
                    0
                ),

            "failure_reason":
                record.get(
                    "failure_reason"
                )

        }

        for payment_id, record
        in states.items()

        if record.get("status")
        == "pending_approval"
    ]

    return {

        "count":
            len(pending),

        "payments":
            pending
    }


# =========================================================
# METRICS
# =========================================================

@app.get("/metrics")
def metrics():

    return calculate_metrics()


# =========================================================
# PLAN
# =========================================================

@app.get("/plan/{payment_id}")
def get_plan(payment_id: str):

    plan = create_plan(
        payment_id
    )

    if not plan:

        raise HTTPException(

            status_code=404,

            detail=
                "Payment not found in recovery dataset."
        )

    analysis = analyze_payment(

        plan["payment"],

        plan["customer"],

        plan["subscription"]
    )

    policy = evaluate_policy(

        plan["payment"],

        analysis
    )

    return {

        "payment_id":
            payment_id,

        "payment":
            plan["payment"],

        "analysis":
            analysis,

        "policy":
            policy,

        "action":
            policy["action"],

        "recommendation":
            analysis.get(
                "recommendation"
            )
    }


# =========================================================
# APPROVE
# =========================================================

@app.post("/approve/{payment_id}")
def approve(payment_id: str):

    try:

        return approve_recovery(
            payment_id
        )

    except ValueError as error:

        raise HTTPException(

            status_code=400,

            detail=str(error)
        )


# =========================================================
# REJECT
# =========================================================

@app.post("/reject/{payment_id}")
def reject(payment_id: str):

    try:

        return reject_recovery(
            payment_id
        )

    except ValueError as error:

        raise HTTPException(

            status_code=400,

            detail=str(error)
        )


# =========================================================
# AUDIT
# =========================================================

@app.get("/audit")
def audit_log():

    return {

        "audit_log":
            get_audit_log()
    }


@app.get("/audit/{payment_id}")
def audit_log_for_payment(
    payment_id: str
):

    log = [

        event

        for event in get_audit_log()

        if event.get(
            "payment_id"
        )
        == payment_id
    ]

    return {

        "payment_id":
            payment_id,

        "audit_log":
            log
    }


# =========================================================
# SUPPORT
# =========================================================

@app.get("/support/{payment_id}")
def support(payment_id: str):

    record = get_payment_state(
        payment_id
    )

    if not record:

        raise HTTPException(

            status_code=404,

            detail=
                "Payment not found."
        )

    analysis = (
        record.get("analysis")
        or {}
    )

    policy = (
        record.get("policy")
        or {}
    )

    verification = (
        record.get("verification")
    )

    status = (
        record.get("status")
    )

    next_action_by_status = {

        "recovered":
            "No further action needed - payment recovered.",

        "pending_approval":
            "Awaiting merchant approval to retry this payment.",

        "escalated":
            "Escalated for manual review - see escalation details below.",

        "verification_failed":
            "Recovery attempt failed verification; manual retry or escalation recommended.",

        "blocked":
            "Automated recovery not recommended; consider manual customer outreach.",

        "rejected":
            "Merchant rejected recovery; no further automated action will be taken.",

        "failed":
            "Payment failed; recovery pipeline has not yet completed for it."
    }

    next_action = next_action_by_status.get(

        status,

        "Monitor payment; no action taken yet."
    )

    recovered_amount = (

        record.get("amount")

        if (

            status == "recovered"

            and
            (verification or {}).get(
                "verified"
            )
        )

        else None
    )

    return {

        "payment_id":
            payment_id,

        "amount":
            record.get(
                "amount",
                0
            ),

        "failure_reason":
            record.get(
                "failure_reason"
            ),

        "recovery_probability":
            analysis.get(
                "recovery_probability"
            ),

        "recovery_score":
            analysis.get(
                "recovery_score"
            ),

        "risk_level":
            analysis.get(
                "risk_level"
            ),

        "root_cause":
            analysis.get(
                "root_cause"
            ),

        "diagnosis":
            analysis.get(
                "root_cause"
            ),

        "recommendation":
            analysis.get(
                "recommendation"
            ),

        "ai_engine":
            analysis.get(
                "ai_engine"
            ),

        "reasons":
            analysis.get(
                "reasons",
                []
            ),

        "reasoning":
            analysis.get(
                "reasoning",
                []
            ),

        "policy_decision":
            policy,

        "action_taken":
            record.get(
                "action"
            ),

        "verification":
            verification,

        "current_status":
            status,

        "recovered_amount":
            recovered_amount,

        "next_recommended_action":
            next_action,

        "escalations":
            get_escalations_for_payment(
                payment_id
            ),

        # Engineering guarantees
        "guardrails": {

            "idempotency":
                True,

            "bounded_actions":
                True,

            "max_recovery_attempts":
                2,

            "verification_required":
                True,

            "auditability":
                True
        }
    }


# =========================================================
# ESCALATION
# =========================================================

@app.post("/escalate/{payment_id}")
def escalate(
    payment_id: str,
    payload: dict = None
):

    record = get_payment_state(
        payment_id
    )

    if not record:

        raise HTTPException(

            status_code=404,

            detail=
                "Payment not found."
        )

    payload = payload or {}

    escalation = create_escalation(

        payment_id,

        reason=payload.get(
            "reason",
            "Manual merchant escalation."
        ),

        severity=payload.get(
            "severity",
            "medium"
        ),

        recommended_action=
            payload.get(
                "recommended_action"
            )
    )

    if record.get(
        "status"
    ) != "recovered":

        save_payment_state(

            payment_id,

            status=
                "escalated"
        )

    add_audit_event(

        payment_id,

        "ESCALATION_CREATED",

        escalation
    )

    return {

        "payment_id":
            payment_id,

        "escalation":
            escalation
    }


@app.post("/recovery/order/{payment_id}")
def create_recovery_checkout_order(payment_id: str):
    """
    Create a new Razorpay Order for a bounded recovery attempt.

    The original failed payment is never modified.
    """

    payment = get_payment_state(payment_id)

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found."
        )

    # Never create another recovery order for a terminal payment.
    if payment.get("status") in TERMINAL_STATES:
        raise HTTPException(
            status_code=400,
            detail=f"Payment is already in terminal state: {payment.get('status')}"
        )

    retry_count = int(payment.get("retry_count", 0))

    # Hard safety limit.
    if retry_count >= 2:
        escalation = create_escalation(
            payment_id,
            reason="Maximum recovery attempts reached.",
            severity="high",
            recommended_action="Manual merchant review.",
        )

        add_audit_event(
            payment_id,
            "BOUNDED_ACTION_STOP",
            {
                "retry_count": retry_count,
                "max_attempts": 2,
                "reason": "Recovery attempt limit reached.",
            },
        )

        raise HTTPException(
            status_code=409,
            detail={
                "message": "Maximum recovery attempts reached.",
                "escalation": escalation,
            },
        )

    amount = int(payment.get("amount", 0))

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Invalid recovery amount."
        )

    order = create_recovery_order(
        amount=amount,
        currency=payment.get("currency", "INR"),
        receipt=f"recoverai_{payment_id}_{retry_count + 1}",
        notes={
            "source": "RecoverAI",
            "type": "recovery",
            "original_payment_id": payment_id,
            "attempt": str(retry_count + 1),
        },
    )

    add_audit_event(
        payment_id,
        "RECOVERY_ORDER_CREATED",
        {
            "order_id": order["id"],
            "amount": amount,
            "attempt": retry_count + 1,
            "max_attempts": 2,
        },
    )

    return {
              "success": True,
              "key_id": RAZORPAY_KEY_ID,
              "order_id": order["id"],
              "amount": order["amount"],
              "currency": order["currency"],
              "original_payment_id": payment_id,
              "attempt": retry_count + 1,
              "max_attempts": 2,
            }
@app.post("/recovery/verify/{payment_id}")
def verify_recovery_checkout(
    payment_id: str,
    payload: dict,
):
    """
    Verify a Razorpay Checkout payment and confirm
    the recovered amount from Razorpay.
    """

    payment = get_payment_state(payment_id)

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Original payment not found."
        )

    order_id = payload.get("razorpay_order_id")
    recovery_payment_id = payload.get("razorpay_payment_id")
    signature = payload.get("razorpay_signature")

    if not order_id or not recovery_payment_id or not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay checkout verification fields."
        )

    try:
        verify_checkout_signature(
            order_id=order_id,
            payment_id=recovery_payment_id,
            signature=signature,
        )
    except Exception:
        add_audit_event(
            payment_id,
            "RECOVERY_SIGNATURE_FAILED",
            {
                "order_id": order_id,
                "recovery_payment_id": recovery_payment_id,
            },
        )

        raise HTTPException(
            status_code=400,
            detail="Razorpay payment signature verification failed."
        )

    expected_amount = int(payment.get("amount", 0))

    verification = verify_payment(
        recovery_payment_id,
        expected_amount,
    )

    if not verification.get("verified"):
        add_audit_event(
            payment_id,
            "RECOVERY_PAYMENT_VERIFICATION_FAILED",
            {
                "order_id": order_id,
                "recovery_payment_id": recovery_payment_id,
                "verification": verification,
            },
        )

        return {
            "success": False,
            "recovered": False,
            "verification": verification,
        }

    # The payment is genuinely captured by Razorpay.
    recovered_amount = int(
        verification["actual_amount"]
    )

    save_payment_state(
        payment_id,
        status="recovered",
        action="RECOVERY_EXECUTED",
        recovered_amount=recovered_amount,
        processor_confirmed=True,
        verification={
            "verified": True,
            "message": "Razorpay recovery payment verified.",
            "checks": {
                "signature_valid": True,
                "processor_confirmed": True,
                "amount_matches_expected": True,
                "status_captured": True,
            },
            "recovery_order_id": order_id,
            "recovery_payment_id": recovery_payment_id,
        },
    )

    add_audit_event(
        payment_id,
        "RECOVERY_PAYMENT_VERIFIED",
        {
            "recovery_order_id": order_id,
            "recovery_payment_id": recovery_payment_id,
            "amount": recovered_amount,
            "processor_confirmed": True,
        },
    )

    add_audit_event(
        payment_id,
        "PAYMENT_RECOVERED",
        {
            "amount": recovered_amount,
            "recovery_order_id": order_id,
            "recovery_payment_id": recovery_payment_id,
            "verified": True,
        },
    )

    return {
        "success": True,
        "recovered": True,
        "payment_id": payment_id,
        "recovery_order_id": order_id,
        "recovery_payment_id": recovery_payment_id,
        "recovered_amount": recovered_amount,
        "verification": verification,
    }

# =========================================================
# RAZORPAY WEBHOOK
# =========================================================
@app.post("/webhook/razorpay")
async def razorpay_webhook(
    request: Request
    ):

    # =====================================================
    # 1. RAW BODY
    # =====================================================

    body = await request.body()

    signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    if not signature:

        raise HTTPException(

            status_code=400,

            detail=
                "Missing X-Razorpay-Signature header."
        )

    # =====================================================
    # 2. SIGNATURE VERIFICATION
    # =====================================================

    try:

        verify_webhook_signature(

            body,

            signature
        )

    except Exception:

        raise HTTPException(

            status_code=400,

            detail=
                "Invalid Razorpay webhook signature."
        )

    # =====================================================
    # 3. JSON
    # =====================================================

    event = await request.json()

    event_type = event.get(
        "event"
    )

    # =====================================================
    # 4. ONLY FAILED PAYMENTS
    # =====================================================

    if event_type != "payment.failed":

        return {

            "status":
                "ignored",

            "event":
                event_type
        }

    # =====================================================
    # 5. RAZORPAY ENTITY
    # =====================================================

    payment = (

        event
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    if not payment:

        raise HTTPException(

            status_code=400,

            detail=
                "Payment entity missing from Razorpay webhook."
        )

    payment_id = payment.get(
        "id"
    )

    if not payment_id:

        raise HTTPException(

            status_code=400,

            detail=
                "Razorpay payment ID missing."
        )

    # =====================================================
    # 6. AMOUNT
    # =====================================================

    amount = payment.get(
        "amount",
        0
    )

    amount_inr = (
        amount / 100
    )

    # =====================================================
    # 7. FAILURE
    # =====================================================

    failure_reason = (

        payment.get(
            "error_reason"
        )

        or

        payment.get(
            "error_description"
        )

        or

        "payment_failed"
    )

    # =====================================================
    # 8. CUSTOMER
    # =====================================================

    customer_id = (

        payment.get(
            "notes",
            {}
        ).get(
            "customer_id"
        )

        if isinstance(
            payment.get("notes"),
            dict
        )

        else None
    )

    if not customer_id:

        customer_id = (
            f"razorpay_{payment_id}"
        )

    # =====================================================
    # 9. IDEMPOTENCY RESERVATION
    # =====================================================

    reserved, existing = reserve_payment(

        payment_id,

        status=
            "failed",

        customer_id=
            customer_id,

        amount=
            amount_inr,

        currency=
            payment.get(
                "currency",
                "INR"
            ),

        failure_reason=
            failure_reason,

        retry_count=
            0,

        razorpay_payment_id=
            payment_id,

        razorpay_method=
            payment.get("method")
    )

    if not reserved:

        add_audit_event(

            payment_id,

            "DUPLICATE_WEBHOOK_BLOCKED",

            {

                "existing_status":
                    existing.get(
                        "status"
                    ),

                "reason":
                    "Payment already reserved."
            }
        )

        return {

            "status":
                "ignored",

            "message":
                "Duplicate webhook blocked by idempotency guard.",

            "payment_id":
                payment_id
        }

    # =====================================================
    # 10. WEBHOOK AUDIT
    # =====================================================

    add_audit_event(

        payment_id,

        "RAZORPAY_PAYMENT_FAILED",

        {

            "payment_id":
                payment_id,

            "amount":
                amount_inr,

            "currency":
                payment.get(
                    "currency"
                ),

            "method":
                payment.get(
                    "method"
                ),

            "error_code":
                payment.get(
                    "error_code"
                ),

            "error_description":
                payment.get(
                    "error_description"
                ),

            "error_reason":
                payment.get(
                    "error_reason"
                )
        }
    )

    # =====================================================
    # 11. PIPELINE START
    # =====================================================

    add_audit_event(

        payment_id,

        "RECOVERY_PIPELINE_STARTED",

        {

            "source":
                "razorpay",

            "event":
                event_type,

            "idempotency":
                "reserved"
        }
    )

    try:

        # =================================================
        # PLAN
        # =================================================

        plan = create_plan(
            payment_id
        )

        if not plan:

            raise HTTPException(

                status_code=404,

                detail=
                    "Unable to create recovery plan."
            )

        # =================================================
        # AI
        # =================================================

        analysis = analyze_payment(

            plan["payment"],

            plan["customer"],

            plan["subscription"]
        )

        add_audit_event(

            payment_id,

            "AI_ANALYSIS_COMPLETE",

            analysis
        )

        # =================================================
        # POLICY
        # =================================================

        policy = evaluate_policy(

            plan["payment"],

            analysis
        )

        add_audit_event(

            payment_id,

            "POLICY_DECISION",

            policy
        )

        save_payment_state(

            payment_id,

            analysis=
                analysis,

            policy=
                policy
        )

        # =================================================
        # ACTION
        # =================================================

        action = policy.get(
            "action"
        )

        verification = None

        escalation = None

        # =================================================
        # AUTO RETRY
        # =================================================

        if action == "AUTO_RETRY":

            add_audit_event(

                payment_id,

                "BOUNDED_AUTO_RETRY_ALLOWED",

                {

                    "max_attempts":
                        2,

                    "current_attempt":
                        0
                }
            )

            (
                _,
                verification,
                escalation
            ) = execute_recovery(

                payment_id,

                amount_inr,

                trigger=
                    "RAZORPAY_PAYMENT_FAILED"
            )

        # =================================================
        # MERCHANT APPROVAL
        # =================================================

        elif action == "RETRY_WITH_APPROVAL":

            save_payment_state(

                payment_id,

                status=
                    "pending_approval",

                action=
                    action
            )

            add_audit_event(

                payment_id,

                "RECOVERY_PENDING_APPROVAL",

                {

                    "action":
                        action,

                    "reason":
                        policy.get(
                            "reason"
                        )
                }
            )

        # =================================================
        # BLOCK
        # =================================================

        else:

            save_payment_state(

                payment_id,

                status=
                    "blocked",

                action=
                    action
            )

            add_audit_event(

                payment_id,

                "RECOVERY_BLOCKED_BY_POLICY",

                {

                    "action":
                        action,

                    "reason":
                        policy.get(
                            "reason"
                        )
                }
            )

        # =================================================
        # RESULT
        # =================================================

        return {

            "status":
                "processed",

            "source":
                "razorpay",

            "payment_id":
                payment_id,

            "amount":
                amount_inr,

            "analysis":
                analysis,

            "policy":
                policy,

            "verification":
                verification,

            "escalation":
                escalation
        }

    except HTTPException:

        raise

    except Exception as error:

        add_audit_event(

            payment_id,

            "PIPELINE_ERROR",

            {

                "error":
                    str(error)
            }
        )

        raise HTTPException(

            status_code=500,

            detail=str(error)
        )