import os
from pathlib import Path
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.razorpay_service import (
    verify_webhook_signature,
    create_recovery_order,
    verify_checkout_signature,
    verify_payment,
    fetch_payment,
)

from backend.planner import create_plan
from backend.policy_engine import evaluate_policy

from backend.feature_engineering import build_features
from backend.analyzer import analyze_payment

from backend.state_manager import (
    get_payment_state,
    save_payment_state,
    get_all_payment_states,
    get_audit_log,
    reserve_payment,
    add_audit_event,
    create_escalation,
)

from backend.actions.recovery import (
    approve_recovery,
    reject_recovery,
    TERMINAL_STATES,
)

from backend.metrics import calculate_metrics



# =========================================================
# ENVIRONMENT
# =========================================================

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")

if not RAZORPAY_KEY_ID:
    print("WARNING: RAZORPAY_KEY_ID is not configured.")


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="RecoverAI"
)


# =========================================================
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
def extract_payment_metadata(payment: dict) -> dict:
    """
    Extract metadata directly from Razorpay payment entity.
    """

    acquirer_data = payment.get("acquirer_data") or {}
    notes = payment.get("notes") or {}

    return {
        "network": {
            "bank": payment.get("bank"),
            "wallet": payment.get("wallet"),
            "vpa": payment.get("vpa"),
            "acquirer_data": acquirer_data,
        },

        "user": {
            "international": payment.get("international"),
            "contact": payment.get("contact"),
            "email": payment.get("email"),
        },

        "failure": {
            "error_code": payment.get("error_code"),
            "error_source": payment.get("error_source"),
            "error_step": payment.get("error_step"),
            "error_reason": payment.get("error_reason"),
            "error_description": payment.get("error_description"),
        },

        "merchant_notes": {
            "checkout_device": notes.get("checkout_device"),
            "cart_session_duration_seconds": notes.get(
                "cart_session_duration_seconds"
            ),
            "user_preferred_language": notes.get(
                "user_preferred_language"
            ),
        },

        "raw_notes": notes,
    }
# =========================================================
# DASHBOARD API
# =========================================================

@app.get("/dashboard/payments")
def get_dashboard_payments():

    state_path = Path(
        "backend/state/recovery_state.json"
    )

    if not state_path.exists():
        return {
            "payments": [],
            "summary": {
                "revenue_at_risk": 0,
                "recoverable": 0,
                "recovered": 0,
                "blocked": 0
            }
        }

    try:

        data = json.loads(
            state_path.read_text(
                encoding="utf-8"
            )
        )

        payments = data.get(
            "payments",
            {}
        )

        result = []

        for payment_id, payment in payments.items():

            analysis = payment.get(
                "analysis",
                {}
            )

            policy = payment.get(
                "policy",
                {}
            )

            result.append({

                "payment_id":
                    payment_id,

                "amount":
                    payment.get(
                        "amount",
                        0
                    ),

                "currency":
                    payment.get(
                        "currency",
                        "INR"
                    ),

                "status":
                    payment.get(
                        "status",
                        "unknown"
                    ),

                "failure_reason":
                    payment.get(
                        "failure_reason",
                        "unknown"
                    ),

                "retry_count":
                    payment.get(
                        "retry_count",
                        0
                    ),

                "recovery_lock":
                    payment.get(
                        "recovery_lock",
                        False
                    ),

                "analysis":
                    analysis,

                "policy":
                    policy,

                "metadata":
                    payment.get(
                        "metadata",
                        {}
                    ),

                "processor_confirmed":
                    payment.get(
                        "processor_confirmed",
                        False
                    ),

                "recovered_amount":
                    payment.get(
                        "recovered_amount",
                        0
                    ),

                "updated_at":
                    payment.get(
                        "updated_at"
                    )
            })

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        revenue_at_risk = 0
        recoverable = 0
        recovered = 0
        blocked = 0

        for payment in result:

            amount = float(
                payment.get(
                    "amount",
                    0
                ) or 0
            )

            status = str(
                payment.get(
                    "status",
                    ""
                )
            ).lower()

            action = str(
                payment.get(
                    "policy",
                    {}
                ).get(
                    "action",
                    ""
                )
            )

            if status in [
                "failed",
                "pending_approval",
                "escalated"
            ]:
                revenue_at_risk += amount

            if action in [
                "AUTO_RETRY",
                "RETRY_WITH_APPROVAL"
            ]:
                recoverable += amount

            if (
                status == "recovered"
                or payment.get(
                    "processor_confirmed"
                ) is True
            ):
                recovered += amount

            if action == "DO_NOT_RETRY":
                blocked += amount

        return {

            "payments":
                result,

            "summary": {

                "revenue_at_risk":
                    revenue_at_risk,

                "recoverable":
                    recoverable,

                "recovered":
                    recovered,

                "blocked":
                    blocked
            }
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
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


@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "RecoverAI"
    }

# =========================================================
# PAYMENTS LIST
# =========================================================
# =========================================================
# PAYMENTS LIST
# =========================================================
# =========================================================
# PAYMENTS LIST
# =========================================================

@app.get("/payments")
def list_payments():

    states = get_all_payment_states()

    payments = []

    for payment_id, record in states.items():

        # -------------------------------------------------
        # Stored AI analysis
        # -------------------------------------------------

        analysis = record.get("analysis") or {}

        # -------------------------------------------------
        # Stored Razorpay metadata
        # -------------------------------------------------

        metadata = record.get("metadata") or {}

        # -------------------------------------------------
        # Stored ML features
        # -------------------------------------------------

        ml_features = record.get("ml_features") or {}

        # -------------------------------------------------
        # Dashboard payment record
        # -------------------------------------------------

        payments.append({

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

            "currency":
                record.get(
                    "currency",
                    "INR"
                ),

            "status":
                record.get(
                    "status"
                ),

            "failure_reason":
                record.get(
                    "failure_reason"
                ),

            "razorpay_payment_id":
                record.get(
                    "razorpay_payment_id",
                    payment_id
                ),

            "razorpay_method":
                record.get(
                    "razorpay_method"
                ),

            # -------------------------------------------------
            # AI
            # -------------------------------------------------

            "recovery_probability":
                analysis.get(
                    "recovery_probability",
                    0
                ),

            "recovery_score":
                analysis.get(
                    "recovery_score",
                    0
                ),

            "risk_level":
                analysis.get(
                    "risk_level"
                ),

            "root_cause":
                analysis.get(
                    "root_cause"
                ),

            "recommendation":
                analysis.get(
                    "recommendation"
                ),

            # -------------------------------------------------
            # Razorpay metadata
            # -------------------------------------------------

            "metadata":
                metadata,

            # -------------------------------------------------
            # ML features
            # -------------------------------------------------

            "ml_features":
                ml_features,

            # -------------------------------------------------
            # Recovery state
            # -------------------------------------------------

            "retry_count":
                record.get(
                    "retry_count",
                    0
                ),

            "max_recovery_attempts":
                2,

            "recovery_lock":
                record.get(
                    "recovery_lock",
                    False
                ),

            "action_taken":
                record.get(
                    "action_taken"
                ),

            "verification":
                record.get(
                    "verification"
                ),

            # -------------------------------------------------
            # Policy
            # -------------------------------------------------

            "policy":
                record.get(
                    "policy",
                    {}
                ),

            # -------------------------------------------------
            # Timestamp
            # -------------------------------------------------

            "updated_at":
                record.get(
                    "updated_at"
                )
        })

    return {

        "count":
            len(payments),

        "payments":
            payments
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

# =========================================================
# PLAN
# =========================================================

# =========================================================
# PLAN
# =========================================================


# =========================================================
# PLAN
# =========================================================

@app.get("/plan/{payment_id}")
def get_plan(payment_id: str):

    # =====================================================
    # 1. GET LOCAL RECOVERY STATE
    # =====================================================

    # =====================================================
# 1. GET LOCAL RECOVERY STATE
# =====================================================

    record = get_payment_state(payment_id)

    if not record:
     raise HTTPException(
        status_code=404,
        detail="Payment not found."
    )
    
    # =====================================================
# 2. GET RAZORPAY PAYMENT ID
# =====================================================

    razorpay_payment_id = record.get(
    "razorpay_payment_id"
)

    if not razorpay_payment_id:
      raise HTTPException(
        status_code=400,
        detail="No Razorpay payment ID associated with this record."
    )
    

   
    # =====================================================
    # 3. FETCH REAL RAZORPAY PAYMENT
    # =====================================================

    try:

        razorpay_payment = fetch_payment(
            razorpay_payment_id
        )

    except Exception as error:

        raise HTTPException(
            status_code=502,
            detail=f"Unable to fetch payment from Razorpay: {error}"
        )

    # =====================================================
    # 4. EXTRACT REAL RAZORPAY METADATA
    # =====================================================

    metadata = extract_payment_metadata(
        razorpay_payment
    )

    # =====================================================
    # 5. BUILD ML FEATURES FROM REAL DATA
    # =====================================================

    ml_features = build_features(
        metadata,
        razorpay_payment
    )

    # =====================================================
    # 6. UPDATE LOCAL STATE
    # =====================================================

    save_payment_state(
        payment_id,

        metadata=metadata,

        ml_features=ml_features,

        razorpay_payment_id=
            razorpay_payment_id,

        amount=(
            razorpay_payment.get(
                "amount",
                0
            ) / 100
        ),

        currency=razorpay_payment.get(
            "currency",
            "INR"
        ),

        status=razorpay_payment.get(
            "status"
        ),

        razorpay_method=razorpay_payment.get(
            "method"
        ),

        failure_reason=(
            razorpay_payment.get(
                "error_reason"
            )
            or
            razorpay_payment.get(
                "error_description"
            )
        )
    )

    # =====================================================
    # 7. AI ANALYSIS
    # =====================================================

    analysis = analyze_payment(
    razorpay_payment,
    record,
    None,
    ml_features
)

    # =====================================================
    # 8. POLICY
    # =====================================================

    policy = evaluate_policy(
        record,
        analysis
    )

    # =====================================================
    # 9. SAVE AI + POLICY
    # =====================================================

    save_payment_state(
        payment_id,

        analysis=analysis,

        policy=policy,

        metadata=metadata,

        ml_features=ml_features
    )

    # =====================================================
    # 10. RESPONSE
    # =====================================================

    return {
        "payment_id": payment_id,

        "razorpay_payment_id":
            razorpay_payment_id,

        "source": "razorpay",

        "payment": razorpay_payment,

        "metadata": metadata,

        "ml_features": ml_features,

        "analysis": analysis,

        "policy": policy,

        "action": policy.get(
            "action"
        ),

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

    # -----------------------------------------------------
    # 1. Get existing RecoverAI state
    # -----------------------------------------------------

    record = get_payment_state(payment_id)

    # -----------------------------------------------------
    # 2. If not in local state, fetch directly from Razorpay
    # -----------------------------------------------------

    if not record:

        try:

            razorpay_payment = fetch_payment(
                payment_id
            )

            # Extract real Razorpay metadata
            metadata = extract_payment_metadata(
                razorpay_payment
            )

            # Build ML features from real metadata
            ml_feature_row = build_features(
                metadata,
                razorpay_payment
            )

                        # Create local RecoverAI record
            record = save_payment_state(
                payment_id,

                status=razorpay_payment.get(
                    "status",
                    "failed"
                ),

                amount=(
                    razorpay_payment.get(
                        "amount",
                        0
                    ) / 100
                ),

                currency=razorpay_payment.get(
                    "currency",
                    "INR"
                ),

                failure_reason=razorpay_payment.get(
                    "error_reason"
                ),

                razorpay_payment_id=payment_id,

                razorpay_method=razorpay_payment.get(
                    "method"
                ),

                metadata=metadata,

                ml_features=ml_feature_row
            )

        except Exception as exc:

            return {
                "payment_id": payment_id,
                "error": "Payment not found in Razorpay",
                "details": str(exc)
            }

    # -----------------------------------------------------
    # 3. Refresh metadata from Razorpay
    # -----------------------------------------------------

    razorpay_payment_id = record.get(
        "razorpay_payment_id"
    )

    if razorpay_payment_id:

        try:

            razorpay_payment = fetch_payment(
                razorpay_payment_id
            )

            metadata = extract_payment_metadata(
                razorpay_payment
            )

            ml_feature_row = build_features(
                metadata,
                razorpay_payment
            )

            save_payment_state(
                payment_id,
                metadata=metadata,
                ml_features=ml_feature_row
            )

            # Keep local record up to date
            record = get_payment_state(
                payment_id
            )

        except Exception as exc:

            print(
                f"Could not fetch Razorpay metadata "
                f"for {payment_id}: {exc}"
            )

    else:

        print(
            f"No Razorpay payment ID stored for {payment_id}"
        )
    # =====================================================
    # ANALYSIS
    # =====================================================

    analysis = (
        record.get("analysis")
        or {}
    )

    policy = (
        record.get("policy")
        or {}
    )

    verification = record.get(
        "verification"
    )

    status = record.get(
        "status"
    )

    # =====================================================
    # NEXT ACTION
    # =====================================================

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

    # =====================================================
    # RECOVERED AMOUNT
    # =====================================================

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

    # =====================================================
    # SUPPORT RESPONSE
    # =====================================================

    return {
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
                "action_taken"
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
            record.get(
                "escalations",
                []
            ),

        "metadata":
            metadata,

        "ml_features":
            ml_feature_row,

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
# PAYMENT METADATA
# =========================================================

# =========================================================
# PAYMENT METADATA
# =========================================================
@app.get("/payments/{payment_id}/metadata")
def payment_metadata(payment_id: str):

    record = get_payment_state(payment_id)

    if not record:
        raise HTTPException(
            status_code=404,
            detail="Payment not found."
        )

    metadata = record.get(
        "metadata",
        {}
    )

    ml_feature_row = record.get(
        "ml_features",
        {}
    )

    razorpay_payment_id = record.get(
        "razorpay_payment_id",
        payment_id
    )

    try:

        razorpay_payment = fetch_payment(
            razorpay_payment_id
        )

        metadata = extract_payment_metadata(
            razorpay_payment
        )

        ml_feature_row = build_features(
            metadata,
            razorpay_payment
        )

        save_payment_state(
            payment_id,
            metadata=metadata,
            ml_features=ml_feature_row
        )

    except Exception as exc:

        import traceback

        print(
            f"Could not fetch Razorpay metadata "
            f"for {payment_id}: {exc}"
        )

        traceback.print_exc()

    return {
        "payment_id":
            payment_id,

        "metadata":
            metadata,

        "ml_features":
            ml_feature_row,

        "failure_reason":
            record.get(
                "failure_reason"
            ),

        "status":
            record.get(
                "status"
            )
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


# =========================================================
# RECOVERY ORDER
# =========================================================

@app.post("/recovery/order/{payment_id}")
def create_recovery_checkout_order(payment_id: str):

    # =====================================================
    # 1. LOAD PAYMENT
    # =====================================================

    payment = get_payment_state(
        payment_id
    )

    if not payment:

        raise HTTPException(
            status_code=404,
            detail="Payment not found."
        )

    # =====================================================
    # 2. RECOVERY LOCK
    # =====================================================

    recovery_lock = payment.get(
        "recovery_lock",
        False
    )

    if recovery_lock:

        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "Recovery attempt already in progress.",

                "payment_id":
                    payment_id,

                "recovery_order_id":
                    payment.get(
                        "recovery_order_id"
                    )
            }
        )

    # =====================================================
    # 3. TERMINAL STATE
    # =====================================================

    current_status = payment.get(
        "status"
    )

    if current_status in TERMINAL_STATES:

        raise HTTPException(
            status_code=400,
            detail=(
                f"Payment is already in terminal state: "
                f"{current_status}"
            )
        )

    # =====================================================
    # 4. RETRY COUNT
    # =====================================================

    try:

        retry_count = int(
            payment.get(
                "retry_count",
                0
            )
        )

    except (TypeError, ValueError):

        retry_count = 0

    # =====================================================
    # 5. HARD SAFETY LIMIT
    # =====================================================

    MAX_RECOVERY_ATTEMPTS = 2

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

        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "Maximum recovery attempts reached.",

                "escalation":
                    escalation
            }
        )

    # =====================================================
    # 6. SET RECOVERY LOCK
    # =====================================================

    save_payment_state(
        payment_id,
        recovery_lock=True,
        recovery_lock_status="IN_PROGRESS"
    )

    # =====================================================
    # 7. AMOUNT
    # =====================================================

    try:

        amount = int(
            payment.get(
                "amount",
                0
            )
        )

    except (TypeError, ValueError):

        amount = 0

    if amount <= 0:

        # IMPORTANT:
        # release lock if validation fails

        save_payment_state(
            payment_id,
            recovery_lock=False,
            recovery_lock_status="FAILED"
        )

        raise HTTPException(
            status_code=400,
            detail="Invalid recovery amount."
        )

    # =====================================================
    # 8. CURRENCY
    # =====================================================

    currency = payment.get(
        "currency",
        "INR"
    )

    if not currency:
        currency = "INR"

    # =====================================================
    # 9. CREATE RAZORPAY ORDER
    # =====================================================

    try:

        order = create_recovery_order(
            amount=amount,
            currency=currency,
            receipt=(
                f"recoverai_"
                f"{payment_id}_"
                f"{retry_count + 1}"
            ),
            notes={
                "source": "RecoverAI",
                "type": "recovery",
                "original_payment_id":
                    payment_id,
                "attempt":
                    str(retry_count + 1)
            }
        )

        # =================================================
        # 10. UPDATE RETRY COUNT + LOCK
        # =================================================

        new_retry_count = retry_count + 1

        save_payment_state(
            payment_id,
            retry_count=new_retry_count,
            recovery_order_id=order["id"],
            recovery_lock=True,
            recovery_lock_status=
                "WAITING_FOR_PAYMENT"
        )

        # =================================================
        # 11. AUDIT
        # =================================================

        add_audit_event(
            payment_id,
            "RECOVERY_ORDER_CREATED",
            {
                "order_id":
                    order["id"],

                "amount":
                    amount,

                "currency":
                    currency,

                "attempt":
                    new_retry_count,

                "max_attempts":
                    MAX_RECOVERY_ATTEMPTS
            }
        )

    except Exception as error:

        # IMPORTANT:
        # release lock when Razorpay order creation fails

        save_payment_state(
            payment_id,
            recovery_lock=False,
            recovery_lock_status="FAILED"
        )

        add_audit_event(
            payment_id,
            "RECOVERY_ORDER_CREATION_FAILED",
            {
                "error":
                    str(error),

                "attempt":
                    retry_count + 1
            }
        )

        raise HTTPException(
            status_code=500,
            detail=
                f"Failed to create recovery order: {error}"
        )

    # =====================================================
    # 12. RESPONSE
    # =====================================================

    return {
        "success": True,
        "key_id": RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "original_payment_id": payment_id,
        "attempt": new_retry_count,
        "max_attempts": MAX_RECOVERY_ATTEMPTS,
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

        save_payment_state(
            payment_id,
            recovery_lock=False,
            recovery_lock_status="FAILED"
        )

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
        recovery_lock=False,
        recovery_lock_status="COMPLETED",
        verification=verification,
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
# MERCHANT APPROVAL
# =========================================================

@app.post("/recovery/approve/{payment_id}")
def approve_recovery_endpoint(
    payment_id: str
):

    try:

        result = approve_recovery(
            payment_id
        )

        return result

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================================================
# MERCHANT REJECTION
# =========================================================



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
            detail="Payment entity missing from Razorpay webhook."
        )

    # =====================================================
    # PAYMENT METADATA EXTRACTION
    # =====================================================

    metadata = extract_payment_metadata(payment)

    payment_id = payment.get(
        "id"
    )

    if not payment_id:
        raise HTTPException(
            status_code=400,
            detail="Razorpay payment ID missing."
        )

    # =====================================================
    # BUILD ML FEATURES
    # =====================================================

    ml_features = build_features(
        metadata,
        payment
    ) 

    # =====================================================
# PAYMENT METADATA EXTRACTION
# =====================================================

    
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
    payment.get("notes", {}).get("customer_id")
    )

    if not customer_id:
      customer_id = None

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
            "payment_id": payment_id,
            "amount": amount_inr,
            "currency": payment.get("currency"),
            "method": payment.get("method"),
            "error_code": payment.get("error_code"),
            "error_description": payment.get(
                "error_description"
            ),
            "error_reason": payment.get(
                "error_reason"
            ),
            "metadata": metadata,
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

            plan["subscription"],

            ml_features
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
           analysis=analysis,
             policy=policy,
             metadata=metadata,
             ml_features=ml_features
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

            save_payment_state(

        payment_id,

        status="recovery_ready",

        action="AUTO_RETRY"
    )

            add_audit_event(

           payment_id,

            "RECOVERY_READY_FOR_CHECKOUT",

           {

              "action":
                "AUTO_RETRY",

              "max_attempts":
                2,
 
              "reason":
                policy.get("reason")
        }
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
    if __name__ == "__main__":
     import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
# =========================================================
# HEALTH CHECK
# =========================================================

 
