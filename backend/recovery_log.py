import json
import os
from datetime import datetime


LOG_FILE = "recovery_history.json"


def record_recovery(payment, recovery):
    """
    Store every recovery attempt so RecoverAI
    can track its historical performance.
    """

    record = {
        "timestamp": datetime.now().isoformat(),
        "payment_id": payment["payment_id"],
        "amount": payment["amount"],
        "action": recovery.get("action"),
        "status": recovery.get("status"),
        "message": recovery.get("message")
    }

    history = []

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as file:
            try:
                history = json.load(file)
            except json.JSONDecodeError:
                history = []

    history.append(record)

    with open(LOG_FILE, "w") as file:
        json.dump(history, file, indent=4)

    return record


def get_recovery_metrics():
    """
    Calculate basic recovery performance metrics.
    """

    if not os.path.exists(LOG_FILE):
        return {
            "total_attempts": 0,
            "successful_recoveries": 0,
            "total_recovered_amount": 0
        }

    with open(LOG_FILE, "r") as file:
        try:
            history = json.load(file)
        except json.JSONDecodeError:
            history = []

    successful = [
        item for item in history
        if item["status"] == "recovered"
    ]

    total_recovered = sum(
        item["amount"]
        for item in successful
    )

    return {
        "total_attempts": len(history),
        "successful_recoveries": len(successful),
        "total_recovered_amount": total_recovered
    }