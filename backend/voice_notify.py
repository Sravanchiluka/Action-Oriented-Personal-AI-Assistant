import pyttsx3
import threading

speech_lock = threading.Lock()


def speak(text):

    def run():

        with speech_lock:

            try:

                engine = pyttsx3.init()

                engine.setProperty("rate", 170)
                engine.setProperty("volume", 1.0)

                engine.say(str(text))
                engine.runAndWait()

                engine.stop()

            except Exception as e:

                print("Voice error:", e)

    thread = threading.Thread(target=run)
    thread.daemon = True
    thread.start()