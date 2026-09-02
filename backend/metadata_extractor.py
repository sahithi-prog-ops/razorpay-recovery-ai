from typing import Any, Dict


def extract_payment_metadata(payment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a Razorpay payment object into a normalized structure.

    This function should be tolerant of missing fields because
    different Razorpay payment methods can expose different data.
    """

    notes = payment.get("notes") or {}

    email = payment.get("email") or ""
    email_domain = ""

    if "@" in email:
        email_domain = email.split("@")[-1].lower()

    cart_duration = notes.get("cart_session_duration_seconds")

    try:
        cart_duration = float(cart_duration) if cart_duration is not None else 0.0
    except (TypeError, ValueError):
        cart_duration = 0.0

    return {
        # Core payment information
        "payment_id": payment.get("id"),
        "amount": payment.get("amount", 0),
        "currency": payment.get("currency", "INR"),
        "method": payment.get("method", "unknown"),

        # Network / payment context
        "bank": payment.get("bank") or "unknown",
        "wallet": payment.get("wallet") or "unknown",
        "international": bool(payment.get("international", False)),

        # Razorpay failure diagnosis
        "error_code": payment.get("error_code") or "unknown",
        "error_description": payment.get("error_description") or "",
        "error_source": payment.get("error_source") or "unknown",
        "error_step": payment.get("error_step") or "unknown",
        "error_reason": payment.get("error_reason") or "unknown",

        # Customer information
        "email_domain": email_domain,
        "contact_present": bool(payment.get("contact")),

        # Acquirer information
        "acquirer_data": payment.get("acquirer_data") or {},

        # Merchant-defined metadata
        "checkout_device": notes.get(
            "checkout_device",
            "unknown"
        ),

        "cart_session_duration_seconds": cart_duration,

        "user_preferred_language": notes.get(
            "user_preferred_language",
            "unknown"
        ),
    }