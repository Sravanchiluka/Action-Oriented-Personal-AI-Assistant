import datetime
import json
import os
import re

import ollama

try:
    from dateparser.search import search_dates
except Exception:
    search_dates = None

from activity_logger import log_activity
from mcp_servers.calendar_server import add_event, create_event_from_text, show_events
from mcp_servers.email_server import send_email
from mcp_servers.file_server import get_latest_uploaded_document, summarize_document
from mcp_servers.notification_server import make_call, push_notification, send_sms
from mcp_servers.notes_server import create_note, show_notes
from mcp_servers.reminder_server import create_reminder, show_reminders
from mcp_servers.web_search_server import web_search
from search_history import save_search
from voice_notify import speak

USER_NAME = "AI Assistant"
USER_PHONE = "+917659958151"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")


def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {"history": [], "facts": []}


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=2)


def ask_ai(messages):
    response = ollama.chat(model="llama3", messages=messages)
    return response["message"]["content"]


def stream_ai(messages):
    response = ollama.chat(model="llama3", messages=messages, stream=True)
    text = ""
    for chunk in response:
        text += chunk["message"]["content"]
    return text


def detect_tool(message):
    prompt = f"""
You are an AI assistant that decides which tool should be used for a request.

Available tools:
create_note
show_notes
create_reminder
show_reminders
add_event
show_calendar
send_email
send_sms
make_call
web_search
summarize_document
daily_plan
none

User message:
{message}

Return ONLY the tool name.
"""

    try:
        response = ask_ai([{"role": "user", "content": prompt}]).strip().lower()
    except Exception:
        return "none"

    allowed_tools = {
        "create_note",
        "show_notes",
        "create_reminder",
        "show_reminders",
        "add_event",
        "show_calendar",
        "send_email",
        "send_sms",
        "make_call",
        "web_search",
        "summarize_document",
        "daily_plan",
        "none",
    }
    return response if response in allowed_tools else "none"


def extract_facts(message):
    patterns = [
        r"\bmy name is ([^.,!?]+)",
        r"\bi am ([^.,!?]+)",
        r"\bi'm ([^.,!?]+)",
        r"\bi like ([^.,!?]+)",
        r"\bi work on ([^.,!?]+)",
    ]

    facts = []
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            facts.append(match.group(0).strip())
    return facts


def update_memory(memory, user_message, assistant_message=None):
    history = memory.get("history", [])
    history.append(
        {
            "role": "user",
            "content": user_message,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        }
    )

    if assistant_message:
        history.append(
            {
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            }
        )

    facts = memory.get("facts", [])
    for fact in extract_facts(user_message):
        if fact not in facts:
            facts.append(fact)

    memory["history"] = history[-20:]
    memory["facts"] = facts[-15:]
    save_memory(memory)


def build_chat_context(memory, user_message):
    facts = memory.get("facts", [])
    history = memory.get("history", [])[-12:]

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful personal AI assistant. Be concise, practical, and friendly. "
                "Use the saved facts when they are relevant."
            ),
        }
    ]

    if facts:
        messages.append(
            {
                "role": "system",
                "content": "Saved user facts:\n- " + "\n- ".join(facts),
            }
        )

    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


def parse_reminder_request(message):
    reminder_body = re.sub(
        r"^(set\s*a?\s*reminder\s*(to)?|remind\s*me\s*(to)?|reminder)\b",
        "",
        message,
        flags=re.IGNORECASE,
    ).strip(" .")
    normalized_body = _normalize_ampm_spacing(reminder_body)
    direct_datetime = extract_datetime(normalized_body)
    if direct_datetime:
        reminder_text = clean_reminder_text(normalized_body)
        if reminder_text:
            return reminder_text, direct_datetime

    matches = None
    if search_dates is not None:
        matches = search_dates(
            normalized_body,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.datetime.now(),
            },
        )

    if matches:
        matched_text, scheduled_for = max(matches, key=lambda item: len(item[0]))
        reminder_text = _remove_first_case_insensitive_match(normalized_body, matched_text)
        reminder_text = re.sub(r"\b(at|on|by)\b", " ", reminder_text, flags=re.IGNORECASE)
        reminder_text = re.sub(r"\s+", " ", reminder_text).strip(" .")

        if reminder_text:
            return reminder_text, scheduled_for.replace(second=0, microsecond=0)

    reminder_time = extract_time(normalized_body)
    if reminder_time:
        reminder_text = clean_reminder_text(normalized_body)
        if reminder_text:
            return reminder_text, reminder_time

    return None, None


def normalize_schedule_time(time_text):
    parsed_time = datetime.datetime.strptime(time_text.upper(), "%I:%M %p")
    return parsed_time.strftime("%H:%M")


def _normalize_ampm_spacing(text):
    return re.sub(r"(\d)(am|pm)\b", r"\1 \2", text, flags=re.IGNORECASE)


def _remove_first_case_insensitive_match(text, fragment):
    return re.sub(re.escape(fragment), " ", text, count=1, flags=re.IGNORECASE)


TIME_PATTERN = re.compile(r"\b(\d{1,2}(?::\d{2})?\s?(?:am|pm)|\d{1,2}:\d{2})\b", re.IGNORECASE)
RELATIVE_MINUTES_PATTERN = re.compile(r"\bin\s+(\d+)\s+minutes?\b", re.IGNORECASE)
RELATIVE_HOURS_PATTERN = re.compile(r"\bafter\s+(\d+)\s+hours?\b", re.IGNORECASE)


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


def extract_relative_datetime(text, base_time=None):
    normalized_text = _normalize_ampm_spacing(text.lower())
    now = base_time or datetime.datetime.now()

    in_minutes_match = RELATIVE_MINUTES_PATTERN.search(normalized_text)
    if in_minutes_match:
        minutes = int(in_minutes_match.group(1))
        return now + datetime.timedelta(minutes=minutes)

    after_hours_match = RELATIVE_HOURS_PATTERN.search(normalized_text)
    if after_hours_match:
        hours = int(after_hours_match.group(1))
        return now + datetime.timedelta(hours=hours)

    return None


def extract_datetime(text, base_time=None):
    normalized_text = _normalize_ampm_spacing(text.lower())
    now = base_time or datetime.datetime.now()

    relative_time = extract_relative_datetime(normalized_text, now)
    if relative_time:
        return relative_time.replace(second=0, microsecond=0)

    target_date = now
    if "tomorrow" in normalized_text:
        target_date = now + datetime.timedelta(days=1)

    standard_time_match = TIME_PATTERN.search(normalized_text)
    if not standard_time_match:
        return None

    normalized_time = _normalize_time_string(standard_time_match.group(1))
    if not normalized_time:
        return None

    hour, minute = [int(value) for value in normalized_time.split(":", 1)]
    scheduled_for = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if "tomorrow" not in normalized_text and "today" not in normalized_text and scheduled_for < now:
        scheduled_for += datetime.timedelta(days=1)

    return scheduled_for


def extract_time(text):
    normalized_text = _normalize_ampm_spacing(text.lower())
    scheduled_for = extract_datetime(normalized_text)
    if scheduled_for:
        return scheduled_for.strftime("%H:%M")

    standard_time_match = TIME_PATTERN.search(normalized_text)
    if not standard_time_match:
        return None

    return _normalize_time_string(standard_time_match.group(1))


def clean_reminder_text(text):
    reminder_text = re.sub(
        r"^(set\s*a?\s*reminder\s*(to)?|remind\s*me\s*(to)?|reminder\s*(to)?)\b",
        "",
        text,
        flags=re.IGNORECASE,
    )
    reminder_text = _normalize_ampm_spacing(reminder_text)
    reminder_text = RELATIVE_MINUTES_PATTERN.sub(" ", reminder_text)
    reminder_text = RELATIVE_HOURS_PATTERN.sub(" ", reminder_text)
    reminder_text = re.sub(r"\b(tomorrow|today)\b", " ", reminder_text, flags=re.IGNORECASE)
    reminder_text = TIME_PATTERN.sub(" ", reminder_text)
    reminder_text = re.sub(r"\b(at|on|by)\b", " ", reminder_text, flags=re.IGNORECASE)
    reminder_text = re.sub(r"\s+", " ", reminder_text)
    return reminder_text.strip(" .")


NOTE_CREATE_PATTERN = re.compile(r"^(?:create|save|add)\s+(?:a\s+)?note\b", re.IGNORECASE)
NOTE_SHOW_PATTERN = re.compile(r"^(?:show\s+)?notes\b", re.IGNORECASE)
REMINDER_CREATE_PATTERN = re.compile(
    r"^(?:set\s+(?:a\s+)?)?reminder\b|^remind\s+me\b",
    re.IGNORECASE,
)
REMINDER_SHOW_PATTERN = re.compile(r"^show\s+reminders\b", re.IGNORECASE)


def extract_note_content(message):
    note = NOTE_CREATE_PATTERN.sub("", message, count=1).strip(" .")
    return note


def auto_task_execution(message):
    prompt = f"""
You are an intelligent AI assistant.

User message:
{message}

If the user mentions an exam or important task,
create a 4 step preparation plan with time.

Example format:

8:00 AM - Revise concepts
10:00 AM - Practice problems
2:00 PM - Mock test
6:00 PM - Final review

Return only the schedule lines.
"""

    response = ask_ai([{"role": "user", "content": prompt}])
    tasks = re.findall(r"\d{1,2}:\d{2}\s?(?:AM|PM)\s-\s.+", response, flags=re.IGNORECASE)
    return tasks


def get_suggestions(message):
    prompt = f"""
You are a helpful AI assistant.

User message:
{message}

Based on this, suggest helpful actions or recommendations.

Examples:
If exam -> suggest study plan.
If bored -> suggest movies.
If weekend -> suggest activities.

Return 3 suggestions only.
"""
    return ask_ai([{"role": "user", "content": prompt}])


def get_movie_suggestions():
    prompt = """
Suggest 5 good movies.

Include:
Movie name - Genre

Example:
Inception - Sci-fi
The Dark Knight - Action
Interstellar - Sci-fi
"""
    return ask_ai([{"role": "user", "content": prompt}])


def get_music_suggestions():
    prompt = """
Suggest 5 popular songs.

Return format:
Song - Artist
"""
    return ask_ai([{"role": "user", "content": prompt}])


def get_productivity_suggestions():
    prompt = """
Give 5 productivity tips for studying or working.
"""
    return ask_ai([{"role": "user", "content": prompt}])


def _handle_fast_commands(raw_message, normalized, memory):
    if NOTE_CREATE_PATTERN.match(raw_message) or normalized.startswith("note "):
        note = extract_note_content(raw_message)
        if not note:
            return "Please tell me what note to save."

        result = create_note(note)
        log_activity("Created note", note)
        update_memory(memory, raw_message, result)
        return result

    if NOTE_SHOW_PATTERN.match(raw_message):
        result = show_notes() or "No notes available."
        log_activity("Viewed notes")
        update_memory(memory, raw_message, result)
        speak(result)
        return result

    if REMINDER_CREATE_PATTERN.match(raw_message):
        reminder_text, reminder_time = parse_reminder_request(raw_message)
        if not reminder_text or not reminder_time:
            return "Please specify a time like '7pm', 'tomorrow 6pm', 'in 30 minutes', or '19:30'."

        result = create_reminder(reminder_text, reminder_time)
        log_activity("Created reminder", result)
        push_notification(
            "reminder",
            "Reminder scheduled",
            result,
        )
        update_memory(memory, raw_message, result)
        speak("Reminder set.")
        return result

    if REMINDER_SHOW_PATTERN.match(raw_message):
        result = show_reminders()
        log_activity("Viewed reminders")
        update_memory(memory, raw_message, result)
        speak(result)
        return result

    if any(keyword in normalized for keyword in ["schedule", "add event", "meeting"]):
        result = create_event_from_text(raw_message)
        log_activity("Added calendar event", raw_message)
        update_memory(memory, raw_message, result)
        speak("Event scheduled.")
        return result

    if "show calendar" in normalized or "show events" in normalized:
        result = show_events()
        log_activity("Viewed calendar")
        update_memory(memory, raw_message, result)
        speak(result)
        return result

    if normalized.startswith("search "):
        query = raw_message[7:].strip()
        save_search(query)
        results = web_search(query)
        log_activity("Ran web search", query)

        if not results:
            return "No search results found."

        snippets = []
        sources = []
        for item in results:
            snippets.append(f"{item['title']} - {item['snippet']}")
            sources.append(f"- {item['link']}")

        prompt = f"""
Use these search results to answer clearly.

Search results:
{chr(10).join(snippets)}

Question:
{query}
"""

        ai_answer = ask_ai([{"role": "user", "content": prompt}])
        result = f"{ai_answer}\n\nSources:\n" + "\n".join(sources)
        update_memory(memory, raw_message, result)
        speak("Here are the search results.")
        return result

    if "summarize pdf" in normalized or "summarize document" in normalized or "summarize file" in normalized:
        file_path = get_latest_uploaded_document()
        if not file_path:
            return "No supported document uploaded yet."

        result = summarize_document(file_path)
        log_activity("Summarized document", os.path.basename(file_path))
        update_memory(memory, raw_message, result)
        return result

    if "send sms" in normalized:
        text = re.sub(r"send sms", "", raw_message, flags=re.IGNORECASE).strip()
        result = send_sms(USER_PHONE, text)
        log_activity("Sent SMS", text)
        update_memory(memory, raw_message, result)
        return result

    if "call me" in normalized:
        text = re.sub(r"call me", "", raw_message, flags=re.IGNORECASE).strip()
        result = make_call(USER_PHONE, text)
        log_activity("Made call", text)
        update_memory(memory, raw_message, result)
        return result

    return None


def fast_command_handler(message):
    raw_message = message.strip()
    if not raw_message:
        return None

    memory = load_memory()
    return _handle_fast_commands(raw_message, raw_message.lower(), memory)


def process_message(message):
    try:
        raw_message = message.strip()
        normalized = raw_message.lower()
        memory = load_memory()

        fast_result = _handle_fast_commands(raw_message, normalized, memory)
        if fast_result is not None:
            return fast_result

        if "plan my tomorrow" in normalized or "plan tomorrow" in normalized:
            tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%A")
            prompt = f"""
Create a productive daily plan for tomorrow ({tomorrow}).

Return format:

7:00 AM - Wake up
9:00 AM - Deep work / study
1:00 PM - Lunch
6:00 PM - Workout
9:00 PM - Review and prepare for the next day
"""
            plan = ask_ai([{"role": "user", "content": prompt}])
            result = f"Tomorrow's Plan\n\n{plan}"
            log_activity("Generated daily plan", f"tomorrow ({tomorrow})")
            update_memory(memory, raw_message, result)
            speak("Your plan for tomorrow is ready.")
            return result

        if "plan my day" in normalized or "daily plan" in normalized:
            today = datetime.datetime.now().strftime("%A")
            prompt = f"""
Create a productive daily plan for today ({today}).

Return format:

8:00 AM - Morning routine
10:00 AM - Study / work
1:00 PM - Lunch
4:00 PM - Learning
8:00 PM - Review day
"""
            plan = ask_ai([{"role": "user", "content": prompt}])
            result = f"AI Daily Planner\n\n{plan}"
            log_activity("Generated daily plan", today)
            update_memory(memory, raw_message, result)
            speak("Your daily plan is ready.")
            return result

        if any(keyword in normalized for keyword in ["exam", "test", "interview"]):
            tasks = auto_task_execution(raw_message)

            if tasks:
                saved_tasks = []

                for task in tasks:
                    add_event(task)

                    time_text, reminder_text = [part.strip() for part in task.split("-", 1)]
                    reminder_time = normalize_schedule_time(time_text)
                    create_reminder(reminder_text, reminder_time)
                    push_notification(
                        "planner",
                        "Auto task scheduled",
                        f"{reminder_text} at {time_text}",
                    )
                    saved_tasks.append(task)

                result = "I created a preparation plan for you:\n\n" + "\n".join(saved_tasks)
                log_activity("Auto task execution", raw_message)
                update_memory(memory, raw_message, result)
                speak(result)
                return result

        if "productivity" in normalized or "how to focus" in normalized:
            result = get_productivity_suggestions()
            log_activity("Generated productivity suggestions")
            update_memory(memory, raw_message, result)
            speak(result)
            return result

        if "movie" in normalized or "movies" in normalized:
            result = get_movie_suggestions()
            log_activity("Generated movie suggestions")
            update_memory(memory, raw_message, result)
            speak(result)
            return result

        if "song" in normalized or "music" in normalized:
            result = get_music_suggestions()
            log_activity("Generated music suggestions")
            update_memory(memory, raw_message, result)
            speak(result)
            return result

        if "suggest" in normalized or "recommend" in normalized:
            suggestions = get_suggestions(raw_message)
            result = "Here are some suggestions:\n\n" + suggestions
            log_activity("Generated AI suggestions", raw_message)
            update_memory(memory, raw_message, result)
            speak(result)
            return result

        if "send email" in normalized:
            match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw_message)
            if not match:
                return "Please provide an email address."

            receiver = match.group(0)
            prompt = f"""
Write a professional email.

Sender: {USER_NAME}
Request:
{raw_message}
"""
            email_text = ask_ai([{"role": "user", "content": prompt}])
            email_result = send_email(receiver, "AI Assistant Email", email_text)
            if email_result.lower().startswith("email failed:"):
                result = f"❌ Failed to send email to {receiver}."
            else:
                result = f"📧 Email sent to {receiver} successfully!"
            log_activity("Sent email", receiver)
            update_memory(memory, raw_message, result)
            return result

        tool = detect_tool(raw_message)

        if tool == "create_note":
            note = extract_note_content(raw_message)
            if not note:
                return "Please tell me what note to save."
            result = create_note(note)
            log_activity("Created note", note)
            update_memory(memory, raw_message, result)
            return result

        if tool == "show_notes":
            result = show_notes() or "No notes available."
            log_activity("Viewed notes")
            update_memory(memory, raw_message, result)
            speak(result)
            return result

        if tool == "create_reminder":
            reminder_text, reminder_time = parse_reminder_request(raw_message)
            if reminder_text and reminder_time:
                result = create_reminder(reminder_text, reminder_time)
                log_activity("Created reminder", result)
                push_notification("reminder", "Reminder scheduled", result)
                update_memory(memory, raw_message, result)
                speak("Reminder set.")
                return result

        if tool == "show_reminders":
            result = show_reminders()
            log_activity("Viewed reminders")
            update_memory(memory, raw_message, result)
            speak(result)
            return result

        if tool == "add_event":
            result = create_event_from_text(raw_message)
            log_activity("Added calendar event", raw_message)
            update_memory(memory, raw_message, result)
            speak("Event scheduled.")
            return result

        if tool == "show_calendar":
            result = show_events()
            log_activity("Viewed calendar")
            update_memory(memory, raw_message, result)
            speak(result)
            return result

        if tool == "daily_plan":
            return process_message("plan my day")

        if tool == "web_search":
            return process_message(f"search {raw_message}")

        if tool == "summarize_document":
            return process_message("summarize document")

        if tool == "send_email":
            return process_message(f"send email {raw_message}")

        if tool == "send_sms":
            return process_message(f"send sms {raw_message}")

        if tool == "make_call":
            return process_message(f"call me {raw_message}")

        ai_response = stream_ai(build_chat_context(memory, raw_message))
        result = ai_response
        log_activity("AI conversation", "stream")
        update_memory(memory, raw_message, result)
        speak(ai_response)
        return result

    except Exception as error:
        import traceback

        print(traceback.format_exc())
        return f"System error: {str(error)}"
