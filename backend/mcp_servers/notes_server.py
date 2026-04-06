import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES_FILE = os.path.join(BASE_DIR, "notes.txt")


def load_notes():
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        return []


def _save_notes(notes):
    with open(NOTES_FILE, "w", encoding="utf-8") as file:
        for note in notes:
            file.write(note + "\n")


def create_note(note):

    with open(NOTES_FILE, "a", encoding="utf-8") as f:
        f.write(note + "\n")

    return f"Note saved: {note}"


def edit_note(index, new_text):
    notes = load_notes()

    if index < 0 or index >= len(notes):
        raise IndexError("Note not found.")

    notes[index] = new_text.strip()
    _save_notes(notes)
    return "Note updated"


def delete_note(index):
    notes = load_notes()

    if index < 0 or index >= len(notes):
        raise IndexError("Note not found.")

    notes.pop(index)
    _save_notes(notes)
    return "Note deleted"


def show_notes():
    notes = load_notes()
    if not notes:
        return "No notes available."
    return "\n".join(notes)
