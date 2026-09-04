from typing import Any, Dict


def extract_payment_metadata(payment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract useful metadata from a Razorpay payment object.

    This function is intentionally defensive:
    missing Razorpay fields become None/empty values instead
    of crashing the recovery pipeline.
    """

    error = payment.get("error") or {}
    notes = payment.get("notes") or {}
    acquirer_data = payment.get("acquirer_data") or {}

    contact = payment.get("contact")
    email = payment.get("email")

    # Razorpay can expose error information in the payment object.
    error_code = (
        payment.get("error_code")
        or error.get("code")
    )

    error_description = (
        payment.get("error_description")
        or error.get("description")
    )

    error_source = (
        payment.get("error_source")
        or error.get("source")
    )

    error_step = (
        payment.get("error_step")
        or error.get("step")
    )

    error_reason = (
        payment.get("error_reason")
        or error.get("reason")
    )

    return {
        "payment_id": payment.get("id"),

        "amount": payment.get("amount"),
        "currency": payment.get("currency"),
        "method": payment.get("method"),

        "network": {
            "bank": payment.get("bank"),
            "wallet": payment.get("wallet"),
            "vpa": payment.get("vpa"),
            "acquirer_data": acquirer_data,
        },

        "user": {
            "international": bool(
                payment.get("international", False)
            ),
            "contact": contact,
            "email": email,
            "email_domain": (
                email.split("@", 1)[1]
                if isinstance(email, str) and "@" in email
                else None
            ),
            "contact_present": bool(contact),
        },

        "merchant_notes": {
            "checkout_device": notes.get(
                "checkout_device"
            ),
            "cart_session_duration_seconds": notes.get(
                "cart_session_duration_seconds"
            ),
            "user_preferred_language": notes.get(
                "user_preferred_language"
            ),
        },

        "raw_notes": notes,

        "error": {
            "code": error_code,
            "description": error_description,
            "source": error_source,
            "step": error_step,
            "reason": error_reason,
        }
    }