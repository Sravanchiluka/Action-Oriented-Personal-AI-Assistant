import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACTIVITY_LOG_FILE = os.path.join(BASE_DIR, "activity_log.json")


def log_activity(action, detail=""):
    timestamp = datetime.now().isoformat(timespec="seconds")
    line = f"{timestamp}|{action}|{detail}\n"

    with open(ACTIVITY_LOG_FILE, "a", encoding="utf-8") as file:
        file.write(line)


def get_activity_log(limit=50):
    try:
        with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return []

    activities = []
    for line in reversed(lines[-limit:]):
        parts = line.split("|", 2)
        if len(parts) == 3:
            timestamp, action, detail = parts
            activities.append(
                {
                    "timestamp": timestamp,
                    "action": action,
                    "detail": detail,
                }
            )
        else:
            activities.append(
                {
                    "timestamp": "",
                    "action": line,
                    "detail": "",
                }
            )

    return activities
