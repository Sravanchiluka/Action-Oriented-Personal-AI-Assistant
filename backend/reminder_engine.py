import datetime
import time

from mcp_servers.notification_server import push_notification
from mcp_servers.reminder_server import consume_due_reminders
from voice_notify import speak


def reminder_loop():
    while True:
        try:
            now = datetime.datetime.now()
            for reminder in consume_due_reminders(now):
                text = reminder["text"]
                time_str = reminder["scheduled_for"].strftime("%Y-%m-%d %I:%M %p").replace(" 0", " ")
                reminder_message = f"Reminder: {text}"
                push_notification("reminder", f"Reminder for {time_str}", text)
                speak(reminder_message)
        except Exception as error:
            print(f"Reminder engine error: {error}")

        time.sleep(30)
