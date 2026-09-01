from state_manager import get_all_payment_states


def calculate_metrics():

    states = get_all_payment_states()

    total_failed_payments = 0
    revenue_at_risk = 0
    recovered_revenue = 0
    pending_approvals = 0

    for record in states.values():

        # Only count records that actually came from a failed-payment
        # webhook (i.e. went through the recovery pipeline).
        if not record.get("failure_reason"):
            continue

        amount = record.get("amount", 0) or 0
        status = record.get("status")
        verification = record.get("verification") or {}

        total_failed_payments += 1
        revenue_at_risk += amount

        # A payment only counts as recovered revenue once its status
        # is "recovered" AND verification actually succeeded. In this
        # codebase status is only ever set to "recovered" after a
        # successful verification (see actions/recovery.py), but we
        # check verification.verified explicitly here too so this
        # stays correct even if that invariant ever changes.
        if status == "recovered" and verification.get("verified"):
            recovered_revenue += amount
        elif status == "pending_approval":
            pending_approvals += 1

    if revenue_at_risk > 0:
        recovery_rate = (recovered_revenue / revenue_at_risk) * 100
    else:
        recovery_rate = 0

    return {
        "total_failed_payments": total_failed_payments,
        "revenue_at_risk": revenue_at_risk,
        "recovered_revenue": recovered_revenue,
        "pending_approvals": pending_approvals,
        "recovery_rate": round(recovery_rate, 2)
    }