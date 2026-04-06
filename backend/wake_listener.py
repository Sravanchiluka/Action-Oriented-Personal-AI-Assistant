import time

from voice_notify import speak
from wake_word import listen_wake_word


def run_wake_listener():
    while True:
        try:
            if listen_wake_word():
                speak("Yes, how can I help you?")
        except Exception:
            time.sleep(2)
