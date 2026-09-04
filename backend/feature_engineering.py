def build_features(
    metadata: dict,
    payment: dict | None = None
):
    """
    Convert extracted Razorpay metadata + payment information
    into ML-friendly features.
    """

    metadata = metadata or {}
    payment = payment or {}

    network = metadata.get("network") or {}
    user = metadata.get("user") or {}
    merchant_notes = metadata.get("merchant_notes") or {}
    error = metadata.get("error") or {}

    # ---------------------------------------------------------
    # USER FEATURES
    # ---------------------------------------------------------

    international = user.get(
        "international",
        False
    )

    contact = user.get("contact")

    contact_present = bool(contact)

    # ---------------------------------------------------------
    # NETWORK FEATURES
    # ---------------------------------------------------------

    bank = network.get("bank") or "UNKNOWN"

    wallet = network.get("wallet") or "UNKNOWN"

    acquirer_data = (
        network.get("acquirer_data") or {}
    )

    bank_transaction_id = (
        acquirer_data.get(
            "bank_transaction_id"
        )
    )

    acquirer_transaction_present = (
        1 if bank_transaction_id else 0
    )

    # ---------------------------------------------------------
    # ERROR FEATURES
    # ---------------------------------------------------------

    error_code = (
        payment.get("error_code")
        or error.get("code")
        or "UNKNOWN"
    )

    error_source = (
        payment.get("error_source")
        or error.get("source")
        or "UNKNOWN"
    )

    error_step = (
        payment.get("error_step")
        or error.get("step")
        or "UNKNOWN"
    )

    error_reason = (
        payment.get("error_reason")
        or error.get("reason")
        or "UNKNOWN"
    )

    # ---------------------------------------------------------
    # CHECKOUT FEATURES
    # ---------------------------------------------------------

    checkout_device = (
        merchant_notes.get(
            "checkout_device"
        )
        or "UNKNOWN"
    )

    session_duration = merchant_notes.get(
        "cart_session_duration_seconds"
    )

    if session_duration is None:
        session_duration = 0.0

    try:
        session_duration = float(
            session_duration
        )
    except (TypeError, ValueError):
        session_duration = 0.0

    preferred_language = (
        merchant_notes.get(
            "user_preferred_language"
        )
        or "UNKNOWN"
    )

    # ---------------------------------------------------------
    # RETURN ML FEATURES
    # ---------------------------------------------------------

    return {

        "international":
            int(bool(international)),

        "contact_present":
            int(contact_present),

        "bank":
            str(bank).upper(),

        "wallet":
            str(wallet).upper(),

        "acquirer_transaction_present":
            acquirer_transaction_present,

        "error_code":
            str(error_code).upper(),

        "error_source":
            str(error_source).upper(),

        "error_step":
            str(error_step).upper(),

        "error_reason":
            str(error_reason).upper(),

        "checkout_device":
            str(checkout_device),

        "cart_session_duration_seconds":
            session_duration,

        "user_preferred_language":
            str(preferred_language)
    }