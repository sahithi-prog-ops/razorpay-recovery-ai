import json
import os
import time
from datetime import datetime
from uuid import uuid4


# =========================================================
# STATE FILE
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

STATE_DIR = os.path.join(
    BASE_DIR,
    "state"
)

STATE_FILE = os.path.join(
    STATE_DIR,
    "recovery_state.json"
)


# =========================================================
# ENSURE STATE FILE
# =========================================================

def _ensure_state_file():

    os.makedirs(
        STATE_DIR,
        exist_ok=True
    )

    if not os.path.exists(STATE_FILE):

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "payments": {},
                    "audit_log": [],
                    "escalations": {}
                },
                file,
                indent=2
            )


# =========================================================
# LOAD STATE
# =========================================================

def _load_state():

    _ensure_state_file()

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

    except (
        json.JSONDecodeError,
        OSError
    ):

        data = {}

    if not isinstance(data, dict):

        data = {}

    if not isinstance(
        data.get("payments"),
        dict
    ):

        data["payments"] = {}

    if not isinstance(
        data.get("audit_log"),
        list
    ):

        data["audit_log"] = []

    if not isinstance(
        data.get("escalations"),
        dict
    ):

        data["escalations"] = {}

    return data


# =========================================================
# SAVE STATE
# =========================================================

def _save_state(data):

    _ensure_state_file()

    temp_file = STATE_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=2
        )

        file.flush()

        os.fsync(
            file.fileno()
        )

    try:

        os.replace(
            temp_file,
            STATE_FILE
        )

    except PermissionError:

        # OneDrive / Windows can temporarily lock
        # the target JSON file.

        last_error = None

        for _ in range(5):

            try:

                os.replace(
                    temp_file,
                    STATE_FILE
                )

                return

            except PermissionError as error:

                last_error = error

                time.sleep(0.2)

        # Final fallback: write directly.

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2
            )

            file.flush()

            os.fsync(
                file.fileno()
            )

        if os.path.exists(temp_file):

            try:

                os.remove(temp_file)

            except OSError:

                pass


# =========================================================
# PAYMENT STATE
# =========================================================

def get_payment_state(payment_id):

    state = _load_state()

    return state["payments"].get(
        payment_id
    )


def get_all_payment_states():

    state = _load_state()

    return state["payments"]


# =========================================================
# SAVE / UPDATE PAYMENT
# =========================================================

def save_payment_state(
    payment_id,
    **updates
):

    state = _load_state()

    payments = state["payments"]

    existing = payments.get(
        payment_id,
        {}
    )

    if not isinstance(
        existing,
        dict
    ):

        existing = {}

    for key, value in updates.items():

        if value is not None:

            existing[key] = value

    existing["payment_id"] = payment_id

    existing["updated_at"] = (
        datetime.utcnow().isoformat()
    )

    payments[payment_id] = existing

    _save_state(state)

    return existing


# =========================================================
# AUDIT LOG
# =========================================================

def add_audit_event(
    payment_id,
    event,
    details=None
):

    state = _load_state()

    audit_event = {

        "timestamp":
            datetime.utcnow().isoformat(),

        "payment_id":
            payment_id,

        "event":
            event,

        "details":
            details or {}
    }

    state["audit_log"].append(
        audit_event
    )

    _save_state(state)

    return audit_event


def get_audit_log():

    state = _load_state()

    return state["audit_log"]


# =========================================================
# ESCALATIONS
# =========================================================

def create_escalation(
    payment_id,
    reason,
    severity="medium",
    recommended_action=None
):

    state = _load_state()

    escalation_id = (
        "esc_"
        + uuid4().hex[:10]
    )

    escalation = {

        "escalation_id":
            escalation_id,

        "payment_id":
            payment_id,

        "reason":
            reason,

        "severity":
            severity,

        "status":
            "open",

        "recommended_action":
            recommended_action,

        "created_at":
            datetime.utcnow().isoformat()
    }

    state["escalations"][
        escalation_id
    ] = escalation

    _save_state(state)

    return escalation


def get_escalations_for_payment(
    payment_id
):

    state = _load_state()

    return [

        escalation

        for escalation
        in state["escalations"].values()

        if escalation.get(
            "payment_id"
        ) == payment_id
    ]


# =========================================================
# IDEMPOTENT PAYMENT RESERVATION
# =========================================================

def reserve_payment(
    payment_id,
    status="failed",
    customer_id=None,
    amount=0,
    currency="INR",
    failure_reason="payment_failed",
    retry_count=0,
    razorpay_payment_id=None,
    razorpay_method=None
):

    state = _load_state()

    payment = state["payments"].get(
        payment_id
    )

    # -----------------------------------------------------
    # New payment
    # -----------------------------------------------------

    if not payment:

        payment = {

            "payment_id":
                payment_id,

            "status":
                status,

            "customer_id":
                customer_id,

            "amount":
                amount,

            "currency":
                currency,

            "failure_reason":
                failure_reason,

            "retry_count":
                retry_count,

            "recovery_lock":
                True,

            "recovery_lock_status":
                "PROCESSING",

            "recovery_reserved_at":
                datetime.utcnow().isoformat()
        }

        if razorpay_payment_id is not None:

            payment[
                "razorpay_payment_id"
            ] = razorpay_payment_id

        if razorpay_method is not None:

            payment[
                "razorpay_method"
            ] = razorpay_method

        state["payments"][
            payment_id
        ] = payment

        _save_state(state)

        return True, payment

    # -----------------------------------------------------
    # Existing payment already locked
    # -----------------------------------------------------

    if payment.get(
        "recovery_lock"
    ) is True:

        return False, payment

    # -----------------------------------------------------
    # Existing terminal payment
    # -----------------------------------------------------

    if payment.get("status") in {

        "recovered",

        "escalated",

        "rejected",

        "blocked"

    }:

        return False, payment

    # -----------------------------------------------------
    # Reserve existing payment
    # -----------------------------------------------------

    payment["recovery_lock"] = True

    payment[
        "recovery_lock_status"
    ] = "PROCESSING"

    payment[
        "recovery_reserved_at"
    ] = datetime.utcnow().isoformat()

    state["payments"][
        payment_id
    ] = payment

    _save_state(state)

    return True, payment