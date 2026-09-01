def get_customer(customer_id: str):
    return {
        "customer_id": customer_id,
        "previous_payments": 12,
        "successful_payments": 10,
        "failed_payments": 2,
        "lifetime_value": 45999,
        "active": True
    }