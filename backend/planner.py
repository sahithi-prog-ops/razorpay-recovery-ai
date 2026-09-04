import hashlib

from backend.state_manager import get_payment_state


# =========================================================
# MOCK CUSTOMER DATABASE
# =========================================================

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


# =========================================================
# MOCK SUBSCRIPTION DATABASE
# =========================================================

SUBSCRIPTION_DB = {

    "cus_test_8": {

        "status": "active",

        "previous_failures": 1,
    },

    "cus_test_11": {

        "status": "active",

        "previous_failures": 3,
    },

    "cus_test_demo": {

        "status": "active",

        "previous_failures": 0,
    },
}


# =========================================================
# DETERMINISTIC CUSTOMER FALLBACK
# =========================================================

def _derive_customer_profile(customer_id):

    seed = int(
        hashlib.sha256(
            customer_id.encode()
        ).hexdigest(),
        16
    )

    return {

        "successful_payments":
            3 + (seed % 15),

        "failed_payments":
            seed % 4,

        "lifetime_value":
            5000 + (seed % 45000),
    }


# =========================================================
# DETERMINISTIC SUBSCRIPTION FALLBACK
# =========================================================

def _derive_subscription_profile(customer_id):

    seed = int(
        hashlib.sha256(
            (customer_id + "sub").encode()
        ).hexdigest(),
        16
    )

    return {

        "status":
            "active"
            if seed % 5 != 0
            else "past_due",

        "previous_failures":
            seed % 4,
    }


# =========================================================
# CREATE RECOVERY PLAN
# =========================================================

def create_plan(payment_id):

    """
    Builds the recovery context for a payment already
    registered in state_manager.

    Planner responsibilities:

    1. Load payment state
    2. Build payment context
    3. Resolve customer context
    4. Resolve subscription context

    The planner does NOT perform AI analysis
    and does NOT make the policy decision.
    """

    record = get_payment_state(payment_id)

    if not record:

        return None

    # -----------------------------------------------------
    # CUSTOMER
    # -----------------------------------------------------

    customer_id = (

        record.get("customer_id")

        or
        f"{payment_id}_unknown_customer"
    )

    # -----------------------------------------------------
    # PAYMENT
    # -----------------------------------------------------

    payment = {

        "payment_id":
            payment_id,

        "customer_id":
            customer_id,

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

        "failure_reason":
            record.get(
                "failure_reason",
                "unknown"
            ),

        "retry_count":
            record.get(
                "retry_count",
                0
            ),
    }

    # -----------------------------------------------------
    # CUSTOMER CONTEXT
    # -----------------------------------------------------

    customer = CUSTOMER_DB.get(
        customer_id
    )

    if not customer:

        customer = _derive_customer_profile(
            customer_id
        )

    # -----------------------------------------------------
    # SUBSCRIPTION CONTEXT
    # -----------------------------------------------------

    subscription = SUBSCRIPTION_DB.get(
        customer_id
    )

    if not subscription:

        subscription = _derive_subscription_profile(
            customer_id
        )

    # -----------------------------------------------------
    # FINAL PLAN
    # -----------------------------------------------------

    return {

        "payment":
            payment,

        "customer":
            customer,

        "subscription":
            subscription,
    }