import os
import tempfile

try:
    import whisper
except Exception:
    whisper = None


def speech_to_text(upload_file):
    if whisper is None:
        raise RuntimeError(
            "Voice transcription is not available yet. Install openai-whisper to process audio uploads, "
            "or send a transcript from the frontend."
        )

    suffix = os.path.splitext(upload_file.filename or "voice.webm")[1] or ".webm"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name
        temp_file.write(upload_file.file.read())

    try:
        model = whisper.load_model("base")
        result = model.transcribe(temp_path)
        return result.get("text", "").strip()
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass
