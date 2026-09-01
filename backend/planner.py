import hashlib

from state_manager import get_payment_state


# ---------------------------------------------------------
# Mock customer / subscription context
# ---------------------------------------------------------
# Keyed by customer_id. Payments arriving via the webhook only carry
# customer_id, amount, failure_reason, retry_count, etc. — the richer
# "who is this customer" context that the AI layer needs comes from
# here (stand-in for a real CRM/billing DB call).

CUSTOMER_DB = {
    "cus_test_8": {
        "successful_payments": 14,
        "failed_payments": 2,
        "lifetime_value": 42500,
    },
    "cus_test_11": {
        "successful_payments": 3,
        "failed_payments": 5,
        "lifetime_value": 12800,
    },
    "cus_test_demo": {
        "successful_payments": 8,
        "failed_payments": 1,
        "lifetime_value": 27600,
    },
}

SUBSCRIPTION_DB = {
    "cus_test_8": {"status": "active", "previous_failures": 1},
    "cus_test_11": {"status": "active", "previous_failures": 3},
    "cus_test_demo": {"status": "active", "previous_failures": 0},
}


def _derive_customer_profile(customer_id):
    """Deterministic fallback so any webhook payload can still be
    analyzed during a demo, even for a customer_id we've never seen."""

    seed = int(hashlib.sha256(customer_id.encode()).hexdigest(), 16)

    return {
        "successful_payments": 3 + (seed % 15),
        "failed_payments": seed % 4,
        "lifetime_value": 5000 + (seed % 45000),
    }


def _derive_subscription_profile(customer_id):

    seed = int(hashlib.sha256((customer_id + "sub").encode()).hexdigest(), 16)

    return {
        "status": "active" if seed % 5 != 0 else "past_due",
        "previous_failures": seed % 4,
    }


def create_plan(payment_id):
    """
    Build a recovery plan from the raw payment data captured at webhook
    time plus customer/subscription context.

    Returns None if the payment has never been seen (no webhook / no
    state entry) — the caller treats that as "payment not found in
    recovery dataset".
    """

    record = get_payment_state(payment_id)

    if not record:
        return None

    customer_id = record.get("customer_id") or f"{payment_id}_unknown_customer"

    payment = {
        "payment_id": payment_id,
        "customer_id": customer_id,
        "amount": record.get("amount", 0),
        "currency": record.get("currency", "INR"),
        "failure_reason": record.get("failure_reason", "unknown"),
        "retry_count": record.get("retry_count", 0),
    }

    customer = CUSTOMER_DB.get(customer_id) or _derive_customer_profile(customer_id)
    subscription = SUBSCRIPTION_DB.get(customer_id) or _derive_subscription_profile(customer_id)

    return {
        "payment": payment,
        "customer": customer,
        "subscription": subscription,
    }