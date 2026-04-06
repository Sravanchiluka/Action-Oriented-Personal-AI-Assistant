import datetime
import json
import os
import re

from mcp_servers.reminder_server import create_reminder

try:
    from dateparser.search import search_dates
except Exception:
    search_dates = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALENDAR_FILE = os.path.join(BASE_DIR, "calendar.txt")
STRUCTURED_PREFIX = "EVENT_JSON:"
CONFLICT_WINDOW = datetime.timedelta(hours=1)
TIME_PATTERN = re.compile(r"\b(\d{1,2}(?::\d{2})?\s?(?:am|pm)|\d{1,2}:\d{2})\b", re.IGNORECASE)
RELATIVE_MINUTES_PATTERN = re.compile(r"\bin\s+(\d+)\s+minutes?\b", re.IGNORECASE)
RELATIVE_HOURS_PATTERN = re.compile(r"\b(?:in|after)\s+(\d+)\s+hours?\b", re.IGNORECASE)
RELATIVE_DAYS_PATTERN = re.compile(r"\bin\s+(\d+)\s+days?\b", re.IGNORECASE)
WEEKDAY_REPEAT_PATTERN = re.compile(
    r"\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)
SCHEDULE_PREFIX_PATTERN = re.compile(
    r"^(schedule|add|set|create)\s+(an?\s+)?(event|meeting|appointment)\b",
    re.IGNORECASE,
)


def _now():
    return datetime.datetime.now()


def _load_event_lines():
    try:
        with open(CALENDAR_FILE, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return []


def _save_event_lines(lines):
    os.makedirs(os.path.dirname(CALENDAR_FILE), exist_ok=True)
    with open(CALENDAR_FILE, "w", encoding="utf-8") as file:
        for line in lines:
            file.write(line + "\n")


def _normalize_ampm_spacing(text):
    return re.sub(r"(\d)(am|pm)\b", r"\1 \2", text, flags=re.IGNORECASE)


def _normalize_time_string(time_text):
    normalized_time = _normalize_ampm_spacing(time_text.strip().lower())

    if re.fullmatch(r"\d{1,2}:\d{2}", normalized_time):
        return normalized_time

    twelve_hour_match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s?(am|pm)", normalized_time)
    if not twelve_hour_match:
        return None

    hour = int(twelve_hour_match.group(1))
    minute = int(twelve_hour_match.group(2) or "00")
    period = twelve_hour_match.group(3)

    if hour > 12 or minute > 59:
        return None

    if period == "pm" and hour != 12:
        hour += 12
    if period == "am" and hour == 12:
        hour = 0

    return f"{hour:02d}:{minute:02d}"


def _extract_relative_datetime(text, base_time=None):
    normalized_text = _normalize_ampm_spacing(text.lower())
    now = base_time or _now()

    in_minutes_match = RELATIVE_MINUTES_PATTERN.search(normalized_text)
    if in_minutes_match:
        minutes = int(in_minutes_match.group(1))
        return in_minutes_match.group(0), now + datetime.timedelta(minutes=minutes)

    after_hours_match = RELATIVE_HOURS_PATTERN.search(normalized_text)
    if after_hours_match:
        hours = int(after_hours_match.group(1))
        return after_hours_match.group(0), now + datetime.timedelta(hours=hours)

    in_days_match = RELATIVE_DAYS_PATTERN.search(normalized_text)
    if in_days_match:
        days = int(in_days_match.group(1))
        return in_days_match.group(0), now + datetime.timedelta(days=days)

    return None, None


def _extract_named_period_datetime(text, base_time=None):
    normalized_text = _normalize_ampm_spacing(text.lower())
    now = base_time or _now()
    target_date = now

    if "tomorrow" in normalized_text:
        target_date = now + datetime.timedelta(days=1)

    named_periods = [
        ("tonight", (20, 0)),
        ("this evening", (18, 0)),
        ("evening", (18, 0)),
        ("this morning", (9, 0)),
        ("morning", (9, 0)),
    ]

    for phrase, (hour, minute) in named_periods:
        if phrase not in normalized_text:
            continue

        candidate = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if "tomorrow" not in normalized_text and candidate < now:
            candidate += datetime.timedelta(days=1)
        return phrase, candidate

    return None, None


def _extract_datetime_fallback(text, base_time=None):
    normalized_text = _normalize_ampm_spacing(text.lower())
    now = base_time or _now()

    matched_text, relative_time = _extract_relative_datetime(normalized_text, now)
    if relative_time:
        return matched_text, relative_time.replace(second=0, microsecond=0)

    named_period_match, named_period_time = _extract_named_period_datetime(normalized_text, now)
    if named_period_time:
        return named_period_match, named_period_time

    target_date = now
    if "tomorrow" in normalized_text:
        target_date = now + datetime.timedelta(days=1)
    elif "today" in normalized_text:
        target_date = now

    standard_time_match = TIME_PATTERN.search(normalized_text)
    if not standard_time_match:
        return None, None

    normalized_time = _normalize_time_string(standard_time_match.group(1))
    if not normalized_time:
        return None, None

    hour, minute = [int(value) for value in normalized_time.split(":", 1)]
    event_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if "tomorrow" not in normalized_text and "today" not in normalized_text and event_datetime < now:
        event_datetime += datetime.timedelta(days=1)

    match_parts = []
    if "tomorrow" in normalized_text:
        match_parts.append("tomorrow")
    elif "today" in normalized_text:
        match_parts.append("today")
    match_parts.append(standard_time_match.group(1))
    return " ".join(match_parts).strip(), event_datetime


def _parse_legacy_time(line):
    match = re.match(
        r"^(?P<time>\d{1,2}:\d{2}(?:\s?(?:AM|PM))?)(?:\s*[-|]\s*|\s+)(?P<text>.+)$",
        line,
        re.IGNORECASE,
    )
    if match:
        time_text = match.group("time")
        normalized_time = _normalize_ampm_spacing(time_text)
        if re.fullmatch(r"\d{1,2}:\d{2}\s?(?:AM|PM)", normalized_time, re.IGNORECASE):
            event_time = datetime.datetime.strptime(normalized_time.upper(), "%I:%M %p").time()
        else:
            event_time = datetime.datetime.strptime(normalized_time, "%H:%M").time()
        event_date = _now().date()
        return {
            "title": match.group("text").strip(),
            "datetime": datetime.datetime.combine(event_date, event_time).isoformat(timespec="minutes"),
            "display_time": datetime.datetime.combine(event_date, event_time).strftime("%I:%M %p").lstrip("0"),
            "time": datetime.datetime.combine(event_date, event_time).strftime("%I:%M %p").lstrip("0"),
            "text": match.group("text").strip(),
            "recurring": None,
            "raw": line,
            "source": "legacy",
        }

    reverse_match = re.match(r"^(?P<text>.+?)\s+at\s+(?P<time>\d{1,2}:\d{2}(?:\s?(?:AM|PM))?)$", line, re.IGNORECASE)
    if reverse_match:
        time_text = reverse_match.group("time")
        normalized_time = _normalize_ampm_spacing(time_text)
        if re.fullmatch(r"\d{1,2}:\d{2}\s?(?:AM|PM)", normalized_time, re.IGNORECASE):
            event_time = datetime.datetime.strptime(normalized_time.upper(), "%I:%M %p").time()
        else:
            event_time = datetime.datetime.strptime(normalized_time, "%H:%M").time()
        event_date = _now().date()
        return {
            "title": reverse_match.group("text").strip(),
            "datetime": datetime.datetime.combine(event_date, event_time).isoformat(timespec="minutes"),
            "display_time": datetime.datetime.combine(event_date, event_time).strftime("%I:%M %p").lstrip("0"),
            "time": datetime.datetime.combine(event_date, event_time).strftime("%I:%M %p").lstrip("0"),
            "text": reverse_match.group("text").strip(),
            "recurring": None,
            "raw": line,
            "source": "legacy",
        }

    matched_text, event_datetime = _extract_event_datetime(line)
    if event_datetime:
        title = _cleanup_title(line, matched_text)
        display_time = event_datetime.strftime("%Y-%m-%d %I:%M %p").replace(" 0", " ")
        return {
            "title": title,
            "datetime": event_datetime.isoformat(timespec="minutes"),
            "display_time": display_time,
            "time": display_time,
            "text": title,
            "recurring": None,
            "raw": f"{display_time} - {title}",
            "source": "legacy-parsed",
        }

    return {
        "title": line,
        "datetime": None,
        "display_time": "Anytime",
        "time": "Anytime",
        "text": line,
        "recurring": None,
        "raw": line,
        "source": "legacy",
    }


def _parse_event_line(line):
    if line.startswith(STRUCTURED_PREFIX):
        payload = json.loads(line[len(STRUCTURED_PREFIX) :])
        event_datetime = payload.get("datetime")
        display_time = "Anytime"
        if event_datetime:
            parsed = datetime.datetime.fromisoformat(event_datetime)
            display_time = parsed.strftime("%Y-%m-%d %I:%M %p").replace(" 0", " ")
        title = payload.get("title", "").strip() or "Untitled event"
        recurrence = payload.get("recurring")
        recurrence_suffix = f" ({recurrence})" if recurrence else ""
        return {
            "title": title,
            "datetime": event_datetime,
            "display_time": display_time,
            "time": display_time,
            "text": title,
            "recurring": recurrence,
            "raw": f"{display_time} - {title}{recurrence_suffix}",
            "source": "structured",
        }

    return _parse_legacy_time(line)


def load_events():
    return [_parse_event_line(line) for line in _load_event_lines()]


def _serialize_event(event):
    return STRUCTURED_PREFIX + json.dumps(event, ensure_ascii=True)


def _extract_event_datetime(text):
    fallback_match, fallback_datetime = _extract_datetime_fallback(text)
    if fallback_datetime:
        return fallback_match, fallback_datetime

    if search_dates is None:
        return None, None

    normalized = _normalize_ampm_spacing(text)
    matches = search_dates(
        normalized,
        settings={
            "PREFER_DATES_FROM": "future",
            "RELATIVE_BASE": _now(),
        },
    )

    if not matches:
        return None, None

    matched_text, parsed_datetime = max(matches, key=lambda item: len(item[0]))
    return matched_text, parsed_datetime.replace(second=0, microsecond=0)


def _extract_recurrence(text):
    normalized = text.lower()
    if "daily" in normalized or "every day" in normalized:
        return "daily"
    if WEEKDAY_REPEAT_PATTERN.search(normalized):
        return "weekly"
    if "weekly" in normalized or "every week" in normalized:
        return "weekly"
    if "monthly" in normalized or "every month" in normalized:
        return "monthly"
    return None


def _looks_like_scheduled_request(text):
    normalized = text.lower()
    keywords = [
        "schedule",
        "meeting",
        "appointment",
        "in ",
        "after ",
        "tomorrow",
        "today",
        "next ",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
        "daily",
        "weekly",
        "monthly",
    ]
    return any(keyword in normalized for keyword in keywords)


def _cleanup_title(text, matched_text):
    title = text.strip()
    title = re.sub(r"^(schedule|add)\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\bevent\b", "", title, flags=re.IGNORECASE)
    if matched_text:
        title = re.sub(re.escape(matched_text), " ", title, flags=re.IGNORECASE)
    title = RELATIVE_MINUTES_PATTERN.sub(" ", title)
    title = RELATIVE_HOURS_PATTERN.sub(" ", title)
    title = re.sub(r"\b(tomorrow|today|daily|weekly|monthly|every day|every week|every month)\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(tonight|this evening|evening|this morning|morning)\b", " ", title, flags=re.IGNORECASE)
    title = TIME_PATTERN.sub(" ", title)
    title = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(on|at|for)\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" .,-")
    title = re.sub(r"^(schedule)\s+", "", title, flags=re.IGNORECASE)
    return title or text.strip()


def extract_event_details(text):
    normalized = _normalize_ampm_spacing(text.strip())
    matched_text, event_datetime = _extract_datetime_fallback(normalized)

    if event_datetime is None and search_dates is not None:
        matches = search_dates(
            normalized,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": _now(),
            },
        )
        if matches:
            matched_text, event_datetime = max(matches, key=lambda item: len(item[0]))
            event_datetime = event_datetime.replace(second=0, microsecond=0)

    title = normalized
    if matched_text:
        title = re.sub(re.escape(matched_text), " ", title, count=1, flags=re.IGNORECASE)

    title = SCHEDULE_PREFIX_PATTERN.sub("", title, count=1).strip(" .,-")
    title = _cleanup_title(title, None)
    return title, event_datetime


def _structured_events(events):
    structured = []
    for event in events:
        event_datetime = event.get("datetime")
        if not event_datetime:
            continue
        try:
            structured.append({**event, "dt": datetime.datetime.fromisoformat(event_datetime)})
        except ValueError:
            continue
    return structured


def _find_conflicts(events, event_datetime):
    conflicts = []
    for event in _structured_events(events):
        if abs(event["dt"] - event_datetime) < CONFLICT_WINDOW:
            conflicts.append(event)
    return conflicts


def find_next_slot(events, event_datetime):
    candidate = event_datetime
    while True:
        conflicts = _find_conflicts(events, candidate)
        if not conflicts:
            return candidate
        candidate += datetime.timedelta(hours=1)


def _build_reminder_time(event_datetime):
    now = _now()
    preferred = event_datetime - datetime.timedelta(minutes=10)
    if preferred > now:
        return preferred

    fallback = event_datetime - datetime.timedelta(minutes=2)
    if fallback > now:
        return fallback

    return event_datetime


def create_event_from_text(text):
    events = load_events()
    title, event_datetime = extract_event_details(text)

    if not event_datetime:
        return "Please specify a date and time like 'tomorrow at 5 PM' or 'Friday 2:30 PM'."

    recurrence = _extract_recurrence(text)
    if not title:
        title = "Untitled event"

    conflicts = _find_conflicts(events, event_datetime)
    conflict_note = ""
    if conflicts:
        conflicting_event = conflicts[0]
        rescheduled = find_next_slot(events, event_datetime)
        conflict_note = (
            f"Conflict detected with '{conflicting_event['title']}' at "
            f"{conflicting_event['dt'].strftime('%I:%M %p').lstrip('0')}. "
            f"Rescheduled to {rescheduled.strftime('%I:%M %p').lstrip('0')}."
        )
        event_datetime = rescheduled

    event = {
        "title": title,
        "datetime": event_datetime.isoformat(timespec="minutes"),
        "recurring": recurrence,
        "repeat": recurrence,
    }

    lines = _load_event_lines()
    lines.append(_serialize_event(event))
    _save_event_lines(lines)

    reminder_time = _build_reminder_time(event_datetime)
    reminder_result = create_reminder(title, reminder_time)

    when_text = event_datetime.strftime("%Y-%m-%d %I:%M %p").replace(" 0", " ")
    recurrence_text = f" ({recurrence})" if recurrence else ""
    response_lines = [f"Event scheduled: {title}{recurrence_text} on {when_text}."]
    if conflict_note:
        response_lines.append(conflict_note)
    response_lines.append(reminder_result)
    return "\n".join(response_lines)


def add_event(event):
    if isinstance(event, str):
        stripped = event.strip()
        if not stripped:
            return "Please provide event details."

        if search_dates is not None and _looks_like_scheduled_request(stripped):
            matched_text, event_datetime = _extract_event_datetime(stripped)
            if event_datetime:
                return create_event_from_text(stripped)

        lines = _load_event_lines()
        lines.append(stripped)
        _save_event_lines(lines)
        return f"Event added: {stripped}"

    if isinstance(event, dict):
        lines = _load_event_lines()
        lines.append(_serialize_event(event))
        _save_event_lines(lines)
        return f"Event added: {event.get('title', 'Untitled event')}"

    return "Unsupported event format."


def delete_event(index):
    lines = _load_event_lines()

    if index < 0 or index >= len(lines):
        raise IndexError("Event not found.")

    removed = _parse_event_line(lines.pop(index))
    _save_event_lines(lines)
    return f"Event deleted: {removed.get('title', 'Untitled event')}"


def edit_event(index, text):
    lines = _load_event_lines()

    if index < 0 or index >= len(lines):
        raise IndexError("Event not found.")

    updated_text = text.strip()
    if not updated_text:
        raise ValueError("Event text cannot be empty.")

    title, event_datetime = extract_event_details(updated_text)
    recurrence = _extract_recurrence(updated_text)

    if event_datetime:
        event = {
            "title": title or "Untitled event",
            "datetime": event_datetime.isoformat(timespec="minutes"),
            "recurring": recurrence,
            "repeat": recurrence,
        }
        lines[index] = _serialize_event(event)
    else:
        lines[index] = updated_text

    _save_event_lines(lines)
    return "Event updated"


def clear_events():
    _save_event_lines([])
    return "All events cleared."


def show_events():
    events = load_events()
    if not events:
        return "No calendar events."
    return "\n".join(event["raw"] for event in events)
