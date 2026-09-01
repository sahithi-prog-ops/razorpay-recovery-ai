
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from planner import create_plan
from analyzer import analyze_payment
from policy_engine import evaluate_policy

from razorpay_service import (
    fetch_payment,
    verify_webhook_signature
)

from actions.recovery import (
    approve_recovery,
    reject_recovery,
    execute_recovery,
    TERMINAL_STATES
)

from metrics import calculate_metrics

from state_manager import (
    save_payment_state,
    add_audit_event,
    get_audit_log,
    get_payment_state,
    get_all_payment_states,
    create_escalation,
    get_escalations_for_payment
)


app = FastAPI(title="RecoverAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# HEALTH / ARCHITECTURE
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "RecoverAI",
        "pipeline": [
            "Webhook",
            "Payment Validation",
            "Risk / Detection",
            "AI Analysis",
            "Policy Engine",
            "Recovery Action",
            "Verification",
            "Recovered Revenue",
            "Audit Log",
            "Metrics / Dashboard"
        ]
    }


# ---------------------------------------------------------
# PAYMENTS LIST
# ---------------------------------------------------------

@app.get("/payments")
def list_payments():

    states = get_all_payment_states()

    payments = []

    for payment_id, record in states.items():

        analysis = record.get("analysis") or {}

        payments.append({
            "payment_id": payment_id,
            "customer_id": record.get("customer_id"),
            "amount": record.get("amount", 0),
            "failure_reason": record.get("failure_reason"),
            "recovery_probability": analysis.get("recovery_score", 0),
            "status": record.get("status")
        })

    return {"payments": payments}


# ---------------------------------------------------------
# PENDING APPROVALS
# ---------------------------------------------------------

@app.get("/pending")
def list_pending():

    states = get_all_payment_states()

    pending = [
        {
            "payment_id": payment_id,
            "customer_id": record.get("customer_id"),
            "amount": record.get("amount", 0),
            "failure_reason": record.get("failure_reason")
        }
        for payment_id, record in states.items()
        if record.get("status") == "pending_approval"
    ]

    return {
        "count": len(pending),
        "payments": pending
    }


# ---------------------------------------------------------
# METRICS
# ---------------------------------------------------------

@app.get("/metrics")
def metrics():
    return calculate_metrics()


# ---------------------------------------------------------
# RECOVERY PLAN (read-only, used by the "Review" button)
# ---------------------------------------------------------

@app.get("/plan/{payment_id}")
def get_plan(payment_id: str):

    plan = create_plan(payment_id)

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Payment not found in recovery dataset."
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
        "payment_id": payment_id,
        "payment": plan["payment"],
        "analysis": analysis,
        "policy": policy,
        "action": policy["action"],
        "recommendation": analysis["recommendation"]
    }


# ---------------------------------------------------------
# APPROVE / REJECT
# ---------------------------------------------------------

@app.post("/approve/{payment_id}")
def approve(payment_id: str):
    return approve_recovery(payment_id)


@app.post("/reject/{payment_id}")
def reject(payment_id: str):
    return reject_recovery(payment_id)


# ---------------------------------------------------------
# AUDIT LOG
# ---------------------------------------------------------

@app.get("/audit")
def audit_log():
    return {"audit_log": get_audit_log()}


@app.get("/audit/{payment_id}")
def audit_log_for_payment(payment_id: str):

    log = [
        event for event in get_audit_log()
        if event.get("payment_id") == payment_id
    ]

    return {"payment_id": payment_id, "audit_log": log}


# ---------------------------------------------------------
# AI SUPPORT — merchant-friendly explanation of a payment
# ---------------------------------------------------------

@app.get("/support/{payment_id}")
def support(payment_id: str):

    record = get_payment_state(payment_id)

    if not record:
        raise HTTPException(status_code=404, detail="Payment not found.")

    analysis = record.get("analysis") or {}
    policy = record.get("policy") or {}
    verification = record.get("verification")
    status = record.get("status")

    next_action_by_status = {
        "recovered": "No further action needed - payment recovered.",
        "pending_approval": "Awaiting merchant approval to retry this payment.",
        "escalated": "Escalated for manual review - see escalation details below.",
        "verification_failed": "Recovery attempt failed verification; manual retry or escalation recommended.",
        "blocked": "Automated recovery not recommended; consider manual customer outreach.",
        "rejected": "Merchant rejected recovery; no further automated action will be taken.",
        "failed": "Payment failed; recovery pipeline has not yet completed for it.",
    }

    next_action = next_action_by_status.get(
        status,
        "Monitor payment; no action taken yet."
    )

    recovered_amount = (
        record.get("amount")
        if status == "recovered" and (verification or {}).get("verified")
        else None
    )

    return {
        "payment_id": payment_id,
        "amount": record.get("amount", 0),
        "failure_reason": record.get("failure_reason"),

        # Full AI analysis fields (previously only recovery_probability
        # and diagnosis were exposed here — widened so the frontend can
        # show the complete analysis without fabricating any data).
        "recovery_probability": analysis.get("recovery_probability"),
        "recovery_score": analysis.get("recovery_score"),
        "risk_level": analysis.get("risk_level"),
        "root_cause": analysis.get("root_cause"),
        "diagnosis": analysis.get("root_cause"),
        "recommendation": analysis.get("recommendation"),
        "ai_engine": analysis.get("ai_engine"),

        "policy_decision": policy,
        "action_taken": record.get("action"),
        "verification": verification,
        "current_status": status,
        "recovered_amount": recovered_amount,
        "next_recommended_action": next_action,
        "escalations": get_escalations_for_payment(payment_id)
    }


# ---------------------------------------------------------
# ESCALATION — manual or triggered
# ---------------------------------------------------------

@app.post("/escalate/{payment_id}")
def escalate(payment_id: str, payload: dict = None):

    record = get_payment_state(payment_id)

    if not record:
        raise HTTPException(status_code=404, detail="Payment not found.")

    payload = payload or {}

    reason = payload.get("reason", "Manual merchant escalation.")
    severity = payload.get("severity", "medium")
    recommended_action = payload.get("recommended_action")

    escalation = create_escalation(
        payment_id,
        reason=reason,
        severity=severity,
        recommended_action=recommended_action
    )

    # A payment that has already been successfully recovered keeps its
    # "recovered" status (and its revenue counted in /metrics) even if
    # it's later escalated for something like a post-recovery dispute.
    # Escalation is only allowed to change status for payments that
    # haven't already succeeded.
    if record.get("status") != "recovered":
        save_payment_state(payment_id, status="escalated")

    add_audit_event(payment_id, "ESCALATION_CREATED", escalation)

    return {
        "payment_id": payment_id,
        "escalation": escalation
    }


# ---------------------------------------------------------
# RAZORPAY WEBHOOK SIMULATION
# ---------------------------------------------------------
@app.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):

    from razorpay_service import verify_webhook_signature

    # -------------------------------------------------
    # 1. Read RAW body
    # -------------------------------------------------

    body = await request.body()

    signature = request.headers.get("X-Razorpay-Signature")

    if not signature:
        raise HTTPException(
            status_code=400,
            detail="Missing X-Razorpay-Signature header."
        )

    # -------------------------------------------------
    # 2. Verify Razorpay signature
    # -------------------------------------------------

    try:
        verify_webhook_signature(
            body,
            signature
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay webhook signature."
        )

    # -------------------------------------------------
    # 3. Parse JSON only AFTER signature verification
    # -------------------------------------------------

    event = await request.json()

    event_type = event.get("event")

    # -------------------------------------------------
    # 4. We only need failed payments for recovery
    # -------------------------------------------------

    if event_type != "payment.failed":
        return {
            "status": "ignored",
            "event": event_type
        }

    # -------------------------------------------------
    # 5. Extract real Razorpay payment entity
    # -------------------------------------------------

    payment = (
        event
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    if not payment:
        raise HTTPException(
            status_code=400,
            detail="Payment entity missing from Razorpay webhook."
        )

    payment_id = payment.get("id")

    if not payment_id:
        raise HTTPException(
            status_code=400,
            detail="Razorpay payment ID missing."
        )

    # -------------------------------------------------
    # 6. Convert Razorpay amount from paise to INR
    # -------------------------------------------------

    amount = payment.get("amount", 0)

    amount_inr = amount / 100

    # -------------------------------------------------
    # 7. Extract failure information
    # -------------------------------------------------

    failure_reason = (
        payment.get("error_reason")
        or payment.get("error_description")
        or "payment_failed"
    )

    customer_id = (
        payment.get("notes", {}).get("customer_id")
        if isinstance(payment.get("notes"), dict)
        else None
    )

    if not customer_id:
        customer_id = f"razorpay_{payment_id}"

    # -------------------------------------------------
    # 8. Prevent duplicate processing
    # -------------------------------------------------

    previous_record = get_payment_state(payment_id)

    if previous_record:
        return {
            "status": "ignored",
            "message": "Payment already processed.",
            "payment_id": payment_id
        }

    # -------------------------------------------------
    # 9. Store the real Razorpay payment
    # -------------------------------------------------

    save_payment_state(
        payment_id,
        status="failed",
        customer_id=customer_id,
        amount=amount_inr,
        currency=payment.get("currency", "INR"),
        failure_reason=failure_reason,
        retry_count=0,
        razorpay_payment_id=payment_id,
        razorpay_method=payment.get("method")
    )

    add_audit_event(
        payment_id,
        "RAZORPAY_PAYMENT_FAILED",
        {
            "payment_id": payment_id,
            "amount": amount_inr,
            "currency": payment.get("currency"),
            "method": payment.get("method"),
            "error_code": payment.get("error_code"),
            "error_description": payment.get("error_description"),
            "error_source": payment.get("error_source"),
            "error_step": payment.get("error_step"),
            "error_reason": payment.get("error_reason")
        }
    )

    # -------------------------------------------------
    # 10. Start RecoverAI pipeline
    # -------------------------------------------------

    add_audit_event(
        payment_id,
        "RECOVERY_PIPELINE_STARTED",
        {
            "source": "razorpay",
            "event": event_type
        }
    )

    try:

        plan = create_plan(payment_id)

        if not plan:
            raise HTTPException(
                status_code=404,
                detail="Unable to create recovery plan."
            )

        # -------------------------------------------------
        # AI ANALYSIS
        # -------------------------------------------------

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

        # -------------------------------------------------
        # POLICY
        # -------------------------------------------------

        policy = evaluate_policy(
            plan["payment"],
            analysis
        )

        add_audit_event(
            payment_id,
            "POLICY_DECISION",
            policy
        )

        # -------------------------------------------------
        # RECOVERY ACTION
        # -------------------------------------------------

        action = policy["action"]

        verification = None
        escalation = None

        if action == "AUTO_RETRY":

            save_payment_state(
                payment_id,
                analysis=analysis,
                policy=policy
            )

            _, verification, escalation = execute_recovery(
                payment_id,
                amount_inr,
                trigger="RAZORPAY_PAYMENT_FAILED"
            )

        elif action == "RETRY_WITH_APPROVAL":

            save_payment_state(
                payment_id,
                status="pending_approval",
                action=action,
                analysis=analysis,
                policy=policy
            )

            add_audit_event(
                payment_id,
                "RECOVERY_PENDING_APPROVAL",
                {
                    "action": action
                }
            )

        else:

            save_payment_state(
                payment_id,
                status="blocked",
                action=action,
                analysis=analysis,
                policy=policy
            )

            add_audit_event(
                payment_id,
                "RECOVERY_ACTION",
                {
                    "action": action,
                    "outcome": "blocked"
                }
            )

        return {
            "status": "processed",
            "source": "razorpay",
            "payment_id": payment_id,
            "amount": amount_inr,
            "analysis": analysis,
            "policy": policy,
            "verification": verification,
            "escalation": escalation
        }

    except Exception as error:

        add_audit_event(
            payment_id,
            "PIPELINE_ERROR",
            {
                "error": str(error)
            }
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    # -------------------------------------------------
    # 1. Validate payload
    # -------------------------------------------------

    payment = event.get("payment")

    if not payment:
        raise HTTPException(status_code=400, detail="Payment data missing.")

    payment_id = payment.get("payment_id")

    if not payment_id:
        raise HTTPException(status_code=400, detail="payment_id missing.")

    event_type = event.get("event", "")

    # Fall back to the event type when the payment sub-object omits an
    # explicit status (matches the buildathon payload shape, which
    # sends {"event": "payment.failed", "payment": {...}}).
    incoming_status = payment.get("status")

    if not incoming_status:
        incoming_status = "failed" if event_type == "payment.failed" else "unknown"

    # -------------------------------------------------
    # 2. Capture prior status BEFORE touching state, so a repeat
    #    webhook for an already-resolved payment can't clobber it
    #    back to "failed".
    # -------------------------------------------------

    previous_record = get_payment_state(payment_id)
    previous_status = previous_record.get("status") if previous_record else None

    add_audit_event(payment_id, "WEBHOOK_RECEIVED", {"event": event_type, "payment": payment})

    # -------------------------------------------------
    # 3. Store initial payment state
    # -------------------------------------------------

    save_payment_state(
        payment_id,
        status=(previous_status if previous_status else incoming_status),
        customer_id=payment.get("customer_id"),
        amount=payment.get("amount", 0),
        currency=payment.get("currency", "INR"),
        failure_reason=payment.get("failure_reason"),
        retry_count=payment.get("retry_count", 0)
    )

    # -------------------------------------------------
    # 4. Ignore non-failed payments safely
    # -------------------------------------------------

    if incoming_status != "failed":
        return {
            "status": "ignored",
            "message": "Payment is not failed.",
            "payment_id": payment_id
        }

    # Never re-run the pipeline for a payment already in a terminal
    # state (recovered / rejected / escalated).
    if previous_status in TERMINAL_STATES:
        return {
            "status": "ignored",
            "message": f"Payment already in terminal state '{previous_status}'.",
            "payment_id": payment_id
        }

    add_audit_event(
        payment_id,
        "RECOVERY_PIPELINE_STARTED",
        {"failure_reason": payment.get("failure_reason")}
    )

    try:
        # -------------------------------------------------
        # 5. Create the recovery plan
        # -------------------------------------------------

        plan = create_plan(payment_id)

        if not plan:
            add_audit_event(payment_id, "PLAN_CREATION_FAILED")

            return {
                "status": "error",
                "message": "Payment not found in recovery dataset."
            }

        # -------------------------------------------------
        # 6. AI / risk analysis
        # -------------------------------------------------

        analysis = analyze_payment(
            plan["payment"],
            plan["customer"],
            plan["subscription"]
        )

        add_audit_event(payment_id, "AI_ANALYSIS_COMPLETE", analysis)

        # -------------------------------------------------
        # 7. Policy evaluation
        # -------------------------------------------------

        policy = evaluate_policy(plan["payment"], analysis)

        add_audit_event(payment_id, "POLICY_DECISION", policy)

        # -------------------------------------------------
        # 8-13. Apply the policy decision to state
        # -------------------------------------------------

        action = policy["action"]
        verification = None
        escalation = None

        if action == "AUTO_RETRY":

            save_payment_state(
                payment_id,
                analysis=analysis,
                policy=policy
            )

            _, verification, escalation = execute_recovery(
                payment_id,
                plan["payment"]["amount"],
                trigger="AUTO_RETRY"
            )

        elif action == "RETRY_WITH_APPROVAL":

            save_payment_state(
                payment_id,
                status="pending_approval",
                action=action,
                analysis=analysis,
                policy=policy
            )

            add_audit_event(
                payment_id,
                "RECOVERY_PENDING_APPROVAL",
                {"action": action}
            )

        else:
            # DO_NOT_RETRY / blocked — no automatic recovery attempt,
            # and not routed to merchant approval either.

            save_payment_state(
                payment_id,
                status="blocked",
                action=action,
                analysis=analysis,
                policy=policy
            )

            add_audit_event(
                payment_id,
                "RECOVERY_ACTION",
                {"action": action, "outcome": "blocked", "simulated": True}
            )

        # -------------------------------------------------
        # 14/15. Return the complete pipeline result
        # -------------------------------------------------

        return {
            "status": "processed",
            "payment_id": payment_id,
            "analysis": analysis,
            "policy": policy,
            "verification": verification,
            "escalation": escalation
        }

    except Exception as error:

        add_audit_event(payment_id, "PIPELINE_ERROR", {"error": str(error)})

        raise HTTPException(status_code=500, detail=str(error))
