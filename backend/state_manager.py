import json
import os
import uuid
from datetime import datetime


STATE_FILE = os.path.join(
    os.path.dirname(__file__),
    "state",
    "recovery_state.json"
)


def _load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "payments": {},
            "audit_log": [],
            "escalations": {}
        }

    with open(STATE_FILE, "r") as file:
        try:
            state = json.load(file)
        except json.JSONDecodeError:
            # Corrupt/empty state file — start fresh rather than crash.
            state = {}

    state.setdefault("payments", {})
    state.setdefault("audit_log", [])
    state.setdefault("escalations", {})

    return state


def _save_state(state):
    os.makedirs(
        os.path.dirname(STATE_FILE),
        exist_ok=True
    )

    with open(STATE_FILE, "w") as file:
        json.dump(
            state,
            file,
            indent=2,
            default=str
        )


# ---------------------------------------------------------
# Payment state
# ---------------------------------------------------------

def save_payment_state(
    payment_id,
    status=None,
    action=None,
    amount=None,
    **extra
):
    """
    Merges fields into the existing payment record instead of
    replacing it, so data written by earlier pipeline steps (customer
    info, analysis, policy, verification) is never accidentally
    destroyed by a later call that only touches status/action.
    """

    state = _load_state()

    record = state["payments"].get(payment_id, {})

    if status is not None:
        record["status"] = status

    if action is not None:
        record["action"] = action

    if amount is not None:
        record["amount"] = amount

    record.update(extra)
    record.setdefault("payment_id", payment_id)
    record["updated_at"] = datetime.now().isoformat()

    state["payments"][payment_id] = record

    _save_state(state)

    return record


def get_payment_state(payment_id):
    state = _load_state()

    return state["payments"].get(payment_id)


def get_all_payment_states():
    state = _load_state()

    return state["payments"]


# ---------------------------------------------------------
# Audit log — append-only, never deletes previous events
# ---------------------------------------------------------

def add_audit_event(
    payment_id,
    event,
    details=None
):
    state = _load_state()

    audit_event = {
        "timestamp": datetime.now().isoformat(),
        "payment_id": payment_id,
        "event": event,
        "details": details or {}
    }

    state["audit_log"].append(audit_event)

    _save_state(state)

    return audit_event


def get_audit_log():
    state = _load_state()

    return state.get(
        "audit_log",
        []
    )


# ---------------------------------------------------------
# Escalations
# ---------------------------------------------------------

def create_escalation(
    payment_id,
    reason,
    severity="medium",
    recommended_action=None
):
    state = _load_state()

    escalation_id = f"esc_{uuid.uuid4().hex[:10]}"

    escalation = {
        "escalation_id": escalation_id,
        "payment_id": payment_id,
        "reason": reason,
        "severity": severity,
        "status": "open",
        "recommended_action": (
            recommended_action or "Manual merchant review required."
        ),
        "created_at": datetime.now().isoformat()
    }

    state["escalations"][escalation_id] = escalation

    _save_state(state)

    return escalation


def get_escalations_for_payment(payment_id):
    state = _load_state()

    return [
        escalation
        for escalation in state.get("escalations", {}).values()
        if escalation.get("payment_id") == payment_id
    ]


def get_all_escalations():
    state = _load_state()

    return state.get("escalations", {})