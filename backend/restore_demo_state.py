import json
from pathlib import Path

state_file = Path("state/recovery_state.json")

payments = {
    "pay_test_8": {
        "payment_id": "pay_test_8",
        "customer_id": None,
        "amount": 10958,
        "currency": "INR",
        "failure_reason": None,
        "retry_count": 0,
        "status": "recovered",
        "action": "RETRY_PAYMENT",
        "analysis": {
            "recovery_score": 88,
            "recovery_probability": 0.8778,
            "risk_level": "LOW",
            "root_cause": "Payment failed for an unspecified or processor-level reason.",
            "recommendation": "RETRY",
            "reasons": [
                "Customer has a strong payment history.",
                "Subscription is currently active.",
                "Customer has high lifetime value.",
                "Payment has limited previous retry attempts."
            ],
            "ai_engine": "sklearn"
        }
    },

    "pay_test_11": {
        "payment_id": "pay_test_11",
        "customer_id": "cus_test_11",
        "amount": 90233,
        "currency": "INR",
        "failure_reason": "insufficient_funds",
        "retry_count": 1,
        "status": "rejected",
        "action": "NO_ACTION",
        "analysis": {
            "recovery_score": 59,
            "recovery_probability": 0.59,
            "risk_level": "MEDIUM",
            "root_cause": "Customer has repeated payment failures and insufficient funds.",
            "recommendation": "NO_ACTION",
            "reasons": [
                "Customer has multiple failed payments.",
                "Payment failure reason is insufficient funds."
            ],
            "ai_engine": "sklearn"
        }
    },

    "pay_test_15": {
        "payment_id": "pay_test_15",
        "customer_id": None,
        "amount": 20533,
        "currency": "INR",
        "failure_reason": None,
        "retry_count": 0,
        "status": "rejected",
        "action": "NO_ACTION",
        "analysis": {
            "recovery_score": 96,
            "recovery_probability": 0.9603,
            "risk_level": "LOW",
            "root_cause": "Payment failed for an unspecified or processor-level reason.",
            "recommendation": "RETRY",
            "reasons": [
                "Customer has a strong payment history.",
                "Subscription is currently active.",
                "Customer has high lifetime value.",
                "Payment has limited previous retry attempts."
            ],
            "ai_engine": "sklearn"
        }
    },

    "pay_new_9001": {
        "payment_id": "pay_new_9001",
        "customer_id": "cus_test_8",
        "amount": 15499,
        "currency": "INR",
        "failure_reason": "card_declined",
        "retry_count": 0,
        "status": "recovered",
        "action": "RETRY_PAYMENT",
        "analysis": {
            "recovery_score": 97,
            "recovery_probability": 0.97,
            "risk_level": "LOW",
            "root_cause": "The customer's card was declined.",
            "recommendation": "RETRY",
            "reasons": [
                "Customer has a strong payment history.",
                "Subscription is currently active.",
                "Customer has high lifetime value.",
                "Payment has limited previous retry attempts."
            ],
            "ai_engine": "sklearn"
        },
        "policy": {
            "action": "RETRY_WITH_APPROVAL",
            "requires_merchant_approval": True,
            "reason": "Failure reason 'card_declined' requires additional review before retry."
        },
        "verification": {
            "verified": True,
            "payment_id": "pay_new_9001",
            "amount": 15499,
            "status": "recovered",
            "message": "Recovery verified successfully.",
            "checks": {
                "action_is_retry_payment": True,
                "amount_recorded": True,
                "processor_confirmed": True,
                "amount_matches_expected": True
            }
        }
    },

    "pay_failverify_demo": {
        "payment_id": "pay_failverify_demo",
        "customer_id": "cus_test_8",
        "amount": 2500,
        "currency": "INR",
        "failure_reason": "insufficient_funds",
        "retry_count": 0,
        "status": "escalated",
        "action": "RETRY_PAYMENT",
        "analysis": {
            "recovery_score": 100,
            "recovery_probability": 1.0,
            "risk_level": "LOW",
            "root_cause": "Insufficient funds may be recoverable on a later attempt.",
            "recommendation": "RETRY",
            "reasons": [
                "Customer has a strong payment history.",
                "Subscription is currently active.",
                "Customer has high lifetime value.",
                "Payment has limited previous retry attempts.",
                "Insufficient funds may be recoverable on a later attempt."
            ],
            "ai_engine": "sklearn"
        },
        "verification": {
            "verified": False,
            "payment_id": "pay_failverify_demo",
            "amount": 2500,
            "status": "verification_failed",
            "message": "Recovery verification failed: processor_confirmed.",
            "checks": {
                "action_is_retry_payment": True,
                "amount_recorded": True,
                "processor_confirmed": False,
                "amount_matches_expected": True
            }
        }
    },

    "pay_verify_fields": {
        "payment_id": "pay_verify_fields",
        "customer_id": "cus_test_8",
        "amount": 5000,
        "currency": "INR",
        "failure_reason": "expired_card",
        "retry_count": 0,
        "status": "recovered",
        "action": "RETRY_PAYMENT",
        "analysis": {
            "recovery_score": 97,
            "recovery_probability": 0.967,
            "risk_level": "LOW",
            "root_cause": "The card on file has expired and needs to be updated by the customer before any retry can succeed.",
            "recommendation": "RETRY",
            "reasons": [
                "Customer has a strong payment history.",
                "Subscription is currently active.",
                "Customer has high lifetime value.",
                "Payment has limited previous retry attempts.",
                "This failure reason typically requires customer action or merchant review."
            ],
            "ai_engine": "sklearn"
        },
        "policy": {
            "action": "RETRY_WITH_APPROVAL",
            "requires_merchant_approval": True,
            "reason": "Failure reason 'expired_card' requires additional review before retry."
        },
        "verification": {
            "verified": True,
            "payment_id": "pay_verify_fields",
            "amount": 5000,
            "status": "recovered",
            "message": "Recovery verified successfully.",
            "checks": {
                "action_is_retry_payment": True,
                "amount_recorded": True,
                "processor_confirmed": True,
                "amount_matches_expected": True
            }
        }
    },

    "pay_demo_final": {
        "payment_id": "pay_demo_final",
        "customer_id": "cus_demo_final",
        "amount": 25000,
        "currency": "INR",
        "failure_reason": "insufficient_funds",
        "retry_count": 0,
        "status": "recovered",
        "action": "RETRY_PAYMENT",
        "analysis": {
            "recovery_score": 92,
            "recovery_probability": 0.9157,
            "risk_level": "LOW",
            "root_cause": "The customer's payment method had insufficient funds at the time of the charge. This is often temporary.",
            "recommendation": "RETRY",
            "reasons": [
                "Customer has a strong payment history.",
                "Customer has high lifetime value.",
                "Payment has limited previous retry attempts.",
                "Insufficient funds may be recoverable on a later attempt."
            ],
            "ai_engine": "sklearn"
        },
        "policy": {
            "action": "AUTO_RETRY",
            "requires_merchant_approval": False,
            "reason": "High probability of successful recovery."
        },
        "verification": {
            "verified": True,
            "payment_id": "pay_demo_final",
            "amount": 25000,
            "status": "recovered",
            "message": "Recovery verified successfully.",
            "checks": {
                "action_is_retry_payment": True,
                "amount_recorded": True,
                "processor_confirmed": True,
                "amount_matches_expected": True
            }
        }
    },

    "test_payment": {
        "payment_id": "test_payment",
        "customer_id": "razorpay_test_payment",
        "amount": 499.0,
        "currency": "INR",
        "failure_reason": "payment_failed",
        "retry_count": 0,
        "status": "recovered",
        "action": "RETRY_PAYMENT",
        "razorpay_payment_id": "test_payment",
        "razorpay_method": "card",
        "analysis": {
            "recovery_score": 96,
            "recovery_probability": 0.9629,
            "risk_level": "LOW",
            "root_cause": "Payment failed for an unspecified or processor-level reason.",
            "recommendation": "RETRY",
            "reasons": [
                "Customer has a strong payment history.",
                "Subscription is currently active.",
                "Payment has limited previous retry attempts."
            ],
            "ai_engine": "sklearn"
        },
        "policy": {
            "action": "AUTO_RETRY",
            "requires_merchant_approval": False,
            "reason": "High probability of successful recovery."
        },
        "verification": {
            "verified": True,
            "payment_id": "test_payment",
            "amount": 499.0,
            "status": "recovered",
            "message": "Recovery verified successfully.",
            "checks": {
                "action_is_retry_payment": True,
                "amount_recorded": True,
                "processor_confirmed": True,
                "amount_matches_expected": True
            }
        }
    }
}

state = {
    "payments": payments,
    "audit_log": [],
    "escalations": {}
}

state_file.parent.mkdir(parents=True, exist_ok=True)

with open(state_file, "w", encoding="utf-8") as f:
    json.dump(state, f, indent=2)

print("Demo state restored successfully.")
print("Payments:", len(payments))
print("IDs:", list(payments.keys()))
