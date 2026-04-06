import json
import os
import threading
import asyncio

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from activity_logger import get_activity_log
from ai_engine import fast_command_handler, load_memory, process_message
from integrations.whatsapp_bot import router as whatsapp_router
from mcp_servers.calendar_server import clear_events, delete_event, edit_event, load_events, show_events
from mcp_servers.file_server import save_uploaded_file
from mcp_servers.notes_server import delete_note, edit_note, load_notes, show_notes
from mcp_servers.notification_server import peek_notifications, pop_notifications
from mcp_servers.reminder_server import clear_reminders, list_reminders, show_reminders
from reminder_engine import reminder_loop
from search_history import recent_searches
from voice_input import speech_to_text
from wake_listener import run_wake_listener

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")

app = FastAPI()

thread = threading.Thread(target=reminder_loop, daemon=True)
thread.start()

wake_thread = threading.Thread(target=run_wake_listener, daemon=True)
wake_thread.start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router)


class UserMessage(BaseModel):
    text: str


@app.get("/")
def home():
    return {"message": "AI Personal Assistant Running"}


@app.post("/chat")
async def chat(request: UserMessage):
    fast_response = await asyncio.to_thread(fast_command_handler, request.text)
    if fast_response is not None:
        return {"response": fast_response}

    response = await asyncio.to_thread(process_message, request.text)
    return {"response": response}


@app.get("/notes")
def get_notes():
    return {"notes": show_notes(), "items": load_notes()}


@app.put("/notes/{index}")
def edit_note_api(index: int, text: str = Query(..., min_length=1)):
    try:
        return {"message": edit_note(index, text), "items": load_notes()}
    except IndexError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.delete("/notes/{index}")
def delete_note_api(index: int):
    try:
        return {"message": delete_note(index), "items": load_notes()}
    except IndexError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/reminders")
def get_reminders():
    return {"reminders": show_reminders(), "items": list_reminders()}


@app.delete("/reminders")
def clear_reminders_api():
    return {"message": clear_reminders(), "items": list_reminders()}


@app.get("/calendar")
def get_calendar():
    return {"events": show_events(), "items": load_events()}


@app.delete("/calendar/{index}")
def delete_calendar_event(index: int):
    try:
        return {"message": delete_event(index), "items": load_events()}
    except IndexError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.put("/calendar/{index}")
def edit_calendar_event(index: int, text: str = Query(..., min_length=1)):
    try:
        return {"message": edit_event(index, text), "items": load_events()}
    except IndexError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.delete("/calendar")
def clear_calendar_events():
    return {"message": clear_events(), "items": load_events()}


@app.get("/notifications")
def get_notifications(clear: bool = True):
    if not clear:
        return {"notifications": peek_notifications()}
    return {"notifications": pop_notifications()}


@app.get("/search-history")
def get_search_history():
    return {"history": recent_searches()}


@app.get("/history")
def get_history():
    return {"history": load_memory().get("history", [])}


@app.get("/export-history")
def export_history():
    return FileResponse(
        MEMORY_FILE,
        media_type="application/json",
        filename="neuraldesk_history.json",
    )


@app.delete("/clear-history")
def clear_history():
    memory = load_memory()
    memory["history"] = []

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=2)

    return {"message": "History cleared"}


@app.get("/activity")
def get_activity():
    return {"activities": get_activity_log()}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_bytes = await file.read()
    file_path = save_uploaded_file(file.filename, file_bytes)
    return {
        "message": "file uploaded",
        "filename": file.filename,
        "path": file_path,
    }


@app.post("/voice")
async def voice_input(file: UploadFile | None = File(default=None), transcript: str | None = Form(default=None)):
    text = (transcript or "").strip()

    if not text and file is not None:
        try:
            text = speech_to_text(file)
        except RuntimeError as error:
            raise HTTPException(status_code=501, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(status_code=500, detail=f"Voice transcription failed: {error}") from error

    if not text:
        raise HTTPException(status_code=400, detail="Provide a transcript or an audio file.")

    fast_response = await asyncio.to_thread(fast_command_handler, text)
    if fast_response is not None:
        return {"text": text, "response": fast_response}

    response = await asyncio.to_thread(process_message, text)
    return {"text": text, "response": response}
