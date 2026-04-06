try:
    import speech_recognition as sr
except Exception:
    sr = None


def listen_wake_word():
    if sr is None:
        raise RuntimeError("speechrecognition is not installed.")

    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        audio = recognizer.listen(source)
        text = recognizer.recognize_google(audio)
        return "hey assistant" in text.lower()
