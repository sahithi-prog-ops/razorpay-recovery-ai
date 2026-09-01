def get_subscription(subscription_id: str):
    return {
        "subscription_id": subscription_id,
        "status": "active",
        "plan": "premium",
        "billing_cycle": "monthly",
        "previous_failures": 1
    }