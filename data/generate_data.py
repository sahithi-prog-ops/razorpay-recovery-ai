import csv
import random

random.seed(42)

OUTPUT_FILE = "payments.csv"

FAILURE_REASONS = [
    "insufficient_funds",
    "card_declined",
    "expired_card",
    "network_error",
    "bank_error",
]

rows = []

for i in range(1000):

    amount = random.randint(500, 100000)

    retry_count = random.randint(0, 5)

    successful_payments = random.randint(0, 20)

    failed_payments = random.randint(0, 10)

    lifetime_value = random.randint(1000, 200000)

    subscription_active = random.choice([0, 1])

    previous_failures = random.randint(0, 5)

    failure_reason = random.choice(FAILURE_REASONS)

    # ------------------------------------------------
    # Synthetic recovery behavior
    # ------------------------------------------------

    recovery_score = 0

    # Strong payment history
    if successful_payments >= 8:
        recovery_score += 25
    elif successful_payments >= 4:
        recovery_score += 15

    # Too many failures reduce recovery likelihood
    if failed_payments <= 2:
        recovery_score += 15
    elif failed_payments >= 7:
        recovery_score -= 15

    # Active subscription is a positive signal
    if subscription_active == 1:
        recovery_score += 20

    # Fewer retries are better
    if retry_count == 0:
        recovery_score += 15
    elif retry_count >= 4:
        recovery_score -= 20

    # High customer value
    if lifetime_value >= 50000:
        recovery_score += 15

    # Previous subscription/payment failures
    if previous_failures >= 4:
        recovery_score -= 15

    # Some failure reasons are more recoverable than others
    if failure_reason in ["insufficient_funds", "network_error"]:
        recovery_score += 10

    if failure_reason in ["expired_card", "card_declined"]:
        recovery_score -= 5

    # Add a little randomness so the dataset isn't perfectly deterministic
    recovery_score += random.randint(-10, 10)

    # Convert score into recovery outcome
    recovery_probability = recovery_score / 100

    recovered = 1 if recovery_probability >= 0.45 else 0

    rows.append({
        "payment_id": f"pay_test_{i+1}",
        "amount": amount,
        "retry_count": retry_count,
        "successful_payments": successful_payments,
        "failed_payments": failed_payments,
        "lifetime_value": lifetime_value,
        "subscription_active": subscription_active,
        "previous_failures": previous_failures,
        "failure_reason": failure_reason,
        "recovered": recovered,
    })


# ------------------------------------------------
# Write dataset to CSV
# ------------------------------------------------

fieldnames = [
    "payment_id",
    "amount",
    "retry_count",
    "successful_payments",
    "failed_payments",
    "lifetime_value",
    "subscription_active",
    "previous_failures",
    "failure_reason",
    "recovered",
]

with open(OUTPUT_FILE, "w", newline="") as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(rows)


print(f"Dataset created successfully: {OUTPUT_FILE}")
print(f"Total payment records: {len(rows)}")