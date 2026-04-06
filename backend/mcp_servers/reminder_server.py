import datetime
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMINDER_FILE = os.path.join(BASE_DIR, "reminders.txt")


def _normalize_reminder_text(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def _load_reminder_lines():
    try:
        with open(REMINDER_FILE, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return []


def _next_occurrence_from_time(time_str):
    today = datetime.datetime.now()
    hours, minutes = [int(value) for value in time_str.split(":", 1)]
    scheduled_for = today.replace(hour=hours, minute=minutes, second=0, microsecond=0)

    if scheduled_for < today:
        scheduled_for += datetime.timedelta(days=1)

    return scheduled_for


def _parse_reminder(reminder_line):
    parts = [part.strip() for part in reminder_line.split("|")]

    if len(parts) >= 2:
        text = parts[0]
        stored_value = parts[1]

        try:
            scheduled_for = datetime.datetime.fromisoformat(stored_value)
        except ValueError:
            if re.fullmatch(r"\d{1,2}:\d{2}", stored_value):
                scheduled_for = _next_occurrence_from_time(stored_value)
            else:
                return None

        return {
            "text": text,
            "scheduled_for": scheduled_for,
        }

    return None


def _format_schedule(scheduled_for):
    now = datetime.datetime.now()
    if scheduled_for.date() == now.date():
        return scheduled_for.strftime("%I:%M %p").lstrip("0")
    return scheduled_for.strftime("%Y-%m-%d %I:%M %p").replace(" 0", " ")


def _serialize_reminder(text, scheduled_for):
    return f"{text} | {scheduled_for.isoformat(timespec='minutes')}"


def _save_reminders(reminders):
    os.makedirs(os.path.dirname(REMINDER_FILE), exist_ok=True)
    with open(REMINDER_FILE, "w", encoding="utf-8") as file:
        for reminder in reminders:
            file.write(_serialize_reminder(reminder["text"], reminder["scheduled_for"]) + "\n")


def load_reminders():
    reminders = []
    for line in _load_reminder_lines():
        reminder = _parse_reminder(line)
        if reminder:
            reminders.append(reminder)
    return reminders


def clean_old_reminders(now_datetime=None):
    now_datetime = now_datetime or datetime.datetime.now()
    reminders = load_reminders()
    pending = [reminder for reminder in reminders if reminder["scheduled_for"] > now_datetime]
    pending.sort(key=lambda reminder: reminder["scheduled_for"])
    _save_reminders(pending)
    return pending


def clear_reminders():
    _save_reminders([])
    return "All reminders cleared."


def create_reminder(text, when):
    if isinstance(when, datetime.datetime):
        scheduled_for = when.replace(second=0, microsecond=0)
    elif isinstance(when, str) and re.fullmatch(r"\d{1,2}:\d{2}", when):
        scheduled_for = _next_occurrence_from_time(when)
    else:
        scheduled_for = datetime.datetime.fromisoformat(str(when))

    reminders = load_reminders()
    normalized_text = _normalize_reminder_text(text)
    for reminder in reminders:
        if (
            _normalize_reminder_text(reminder["text"]) == normalized_text
            and reminder["scheduled_for"] == scheduled_for
        ):
            return f"Reminder already exists for {_format_schedule(scheduled_for)}: {reminder['text']}"

    reminders.append({"text": text, "scheduled_for": scheduled_for})
    reminders.sort(key=lambda reminder: reminder["scheduled_for"])
    _save_reminders(reminders)

    return f"Reminder set for {_format_schedule(scheduled_for)}: {text}"


def show_reminders():
    reminders = clean_old_reminders()
    if not reminders:
        return "No reminders found."

    formatted = []
    for index, reminder in enumerate(reminders, start=1):
        formatted.append(f"{index}. {reminder['text']} at {_format_schedule(reminder['scheduled_for'])}")
    return "\n".join(formatted)


def list_reminders():
    reminders = []
    for reminder in clean_old_reminders():
        reminders.append(
            {
                "text": reminder["text"],
                "scheduled_for": reminder["scheduled_for"].isoformat(),
                "display_time": _format_schedule(reminder["scheduled_for"]),
            }
        )
    return reminders


def consume_due_reminders(now_datetime):
    due = []
    pending = []

    for reminder in load_reminders():
        if reminder["scheduled_for"] <= now_datetime:
            due.append(reminder)
        else:
            pending.append(reminder)

    _save_reminders(pending)
    return due
