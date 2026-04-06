import json
import os
from datetime import datetime

try:
    from twilio.rest import Client
except Exception:
    Client = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTIFICATIONS_FILE = os.path.join(BASE_DIR, "notifications.json")

# Twilio credentials
ACCOUNT_SID = "your_account_sid"
AUTH_TOKEN = "your_auth_token"
TWILIO_PHONE = "+1234567890"

client = Client(ACCOUNT_SID, AUTH_TOKEN) if Client else None


def _read_notifications():
    try:
        with open(NOTIFICATIONS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def _write_notifications(notifications):
    with open(NOTIFICATIONS_FILE, "w", encoding="utf-8") as file:
        json.dump(notifications, file, indent=2)


def push_notification(kind, title, message):
    notifications = _read_notifications()
    notifications.append(
        {
            "id": f"{kind}-{datetime.now().timestamp()}",
            "kind": kind,
            "title": title,
            "message": message,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    _write_notifications(notifications)


def pop_notifications():
    notifications = _read_notifications()
    _write_notifications([])
    return notifications


def peek_notifications():
    return _read_notifications()


def send_sms(phone, message):
    if not client:
        return "SMS failed: Twilio client is not configured."

    try:
        client.messages.create(
            body=message,
            from_=TWILIO_PHONE,
            to=phone,
        )
        return f"SMS sent to {phone}"
    except Exception as e:
        return f"SMS failed: {str(e)}"


def make_call(phone, message):
    if not client:
        return "Call failed: Twilio client is not configured."

    try:
        client.calls.create(
            twiml=f"<Response><Say>{message}</Say></Response>",
            from_=TWILIO_PHONE,
            to=phone,
        )
        return f"Call initiated to {phone}"
    except Exception as e:
        return f"Call failed: {str(e)}"
