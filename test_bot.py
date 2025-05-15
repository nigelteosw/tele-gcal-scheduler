import json
from bot import lambda_handler

def main():
    test_event = {
        "body": json.dumps({
            "message": {
                "text": "/upcoming",  # Try /week, /start, etc.
                "chat": {
                    "id": "260013849"  # Replace with your real Telegram ID
                },
                "from": {
                    "username": "nigelus"
                }
            }
        })
    }

    # Simulated AWS context object (empty for basic use)
    class Context: pass
    context = Context()

    # Call the Lambda handler
    response = lambda_handler(test_event, context)
    print("Lambda Response:", response)

if __name__ == "__main__":
    main()
