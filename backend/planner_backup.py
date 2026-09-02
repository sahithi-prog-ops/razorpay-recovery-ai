import hashlib

from state_manager import get_payment_state


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

    """
    Creates deterministic customer information for customers
    that are not present in the mock CUSTOMER_DB.

    The same customer_id always produces the same profile.
    """

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

    """
    Creates deterministic subscription information when the
    customer does not exist in SUBSCRIPTION_DB.
    """

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
    Builds a recovery plan from payment state.

    The payment must already exist in state_manager.
    This prevents the AI from inventing payments that were
    never received through the recovery pipeline.
    """

    record = get_payment_state(payment_id)

    if not record:
        return None

    # -----------------------------------------------------
    # Customer
    # -----------------------------------------------------

    customer_id = (
        record.get("customer_id")
        or f"{payment_id}_unknown_customer"
    )

    # -----------------------------------------------------
    # Payment
    # -----------------------------------------------------

    payment = {

        "payment_id":
            payment_id,

        "customer_id":
            customer_id,

        "amount":
            record.get("amount", 0),

        "currency":
            record.get("currency", "INR"),

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
    # Customer context
    # -----------------------------------------------------

    customer = CUSTOMER_DB.get(
        customer_id
    )

    if not customer:

        customer = _derive_customer_profile(
            customer_id
        )

    # -----------------------------------------------------
    # Subscription context
    # -----------------------------------------------------

    subscription = SUBSCRIPTION_DB.get(
        customer_id
    )

    if not subscription:

        subscription = _derive_subscription_profile(
            customer_id
        )

    # -----------------------------------------------------
    # Final plan
    # -----------------------------------------------------

    return {

        "payment":
            payment,

        "customer":
            customer,

        "subscription":
            subscription,
    }