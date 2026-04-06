import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEARCH_HISTORY_FILE = os.path.join(BASE_DIR, "search_history.json")


def load_search_history():
    try:
        with open(SEARCH_HISTORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_search(query):
    history = load_search_history()
    history.append(query)

    with open(SEARCH_HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history[-100:], file, indent=2)


def recent_searches(limit=25):
    history = load_search_history()
    return list(reversed(history[-limit:]))
