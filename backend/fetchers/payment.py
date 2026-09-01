import csv
import os


DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "payments.csv"
)


def get_payment(payment_id: str):

    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"Payment dataset not found: {DATA_FILE}"
        )

    with open(DATA_FILE, "r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:

            if row["payment_id"] == payment_id:

                return {
                    "payment_id": row["payment_id"],
                    "amount": int(row["amount"]),
                    "currency": "INR",
                    "status": "failed",
                    "failure_reason": row["failure_reason"],
                    "method": "card",
                    "retry_count": int(row["retry_count"])
                }

    raise ValueError(
        f"Payment '{payment_id}' not found in dataset."
    )