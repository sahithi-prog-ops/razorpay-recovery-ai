import os
import razorpay
from dotenv import load_dotenv

load_dotenv("backend/.env")

KEY_ID = os.getenv("RAZORPAY_KEY_ID")
KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = razorpay.Client(
    auth=(KEY_ID, KEY_SECRET)
)

test_cases = [
    {
        "amount": 200,
        "email": "test1@example.com",
        "contact": "9000000001",
        "device": "android",
        "language": "en",
    },
    {
        "amount": 500,
        "email": "test2@example.com",
        "contact": "9000000002",
        "device": "ios",
        "language": "en",
    },
    {
        "amount": 1000,
        "email": "test3@example.com",
        "contact": "9000000003",
        "device": "web",
        "language": "hi",
    },
    {
        "amount": 1500,
        "email": "test4@example.com",
        "contact": "9000000004",
        "device": "android",
        "language": "te",
    },
    {
        "amount": 2500,
        "email": "test5@example.com",
        "contact": "9000000005",
        "device": "web",
        "language": "en",
    },
    {
        "amount": 5000,
        "email": "test6@example.com",
        "contact": "9000000006",
        "device": "ios",
        "language": "hi",
    },
    {
        "amount": 7500,
        "email": "test7@example.com",
        "contact": "9000000007",
        "device": "android",
        "language": "te",
    },
    {
        "amount": 10000,
        "email": "test8@example.com",
        "contact": "9000000008",
        "device": "web",
        "language": "en",
    },
    {
        "amount": 15000,
        "email": "test9@example.com",
        "contact": "9000000009",
        "device": "android",
        "language": "hi",
    },
    {
        "amount": 20000,
        "email": "test10@example.com",
        "contact": "9000000010",
        "device": "ios",
        "language": "en",
    },
]


for i, case in enumerate(test_cases, start=1):

    try:

        link = client.payment_link.create({
            "amount": case["amount"],
            "currency": "INR",

            "description": f"RecoverAI Test Payment {i}",

            "customer": {
                "name": f"RecoverAI Customer {i}",
                "email": case["email"],
                "contact": case["contact"],
            },

            "notes": {
                "source": "RecoverAI",
                "test_case": str(i),
                "checkout_device": case["device"],
                "user_preferred_language": case["language"],
                "cart_session_duration_seconds": str(
                    30 + i * 15
                ),
            },

            "notify": {
                "sms": False,
                "email": False,
            },
        })

        print(
            f"{i:02d}. "
            f"{link['id']} | "
            f"₹{case['amount']} | "
            f"{link['short_url']}"
        )

    except Exception as error:

        print(
            f"{i:02d}. ERROR: {error}"
        )