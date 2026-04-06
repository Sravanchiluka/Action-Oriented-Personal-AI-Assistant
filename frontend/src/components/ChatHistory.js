import React, { useEffect, useState } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

function groupHistory(items) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  const groups = {
    Today: [],
    Yesterday: [],
    "Last Week": [],
    Older: [],
  };

  [...items]
    .reverse()
    .forEach((item) => {
      const parsed = item.timestamp ? new Date(item.timestamp) : null;

      if (!parsed || Number.isNaN(parsed.getTime())) {
        groups.Older.push(item);
        return;
      }

      const itemDate = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
      const diff = today.getTime() - itemDate.getTime();

      if (itemDate.getTime() === today.getTime()) {
        groups.Today.push(item);
        return;
      }

      if (itemDate.getTime() === yesterday.getTime()) {
        groups.Yesterday.push(item);
        return;
      }

      if (diff < 7 * 24 * 60 * 60 * 1000) {
        groups["Last Week"].push(item);
        return;
      }

      groups.Older.push(item);
    });

  return groups;
}

function ChatHistory() {
  const [history, setHistory] = useState([]);

  const loadHistory = () => {
    axios
      .get(`${API}/history`)
      .then((response) => setHistory(response.data.history || []))
      .catch(() => setHistory([]));
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const exportHistory = () => {
    window.open(`${API}/export-history`, "_blank");
  };

  const clearHistory = async () => {
    if (!window.confirm("Clear all history?")) {
      return;
    }

    try {
      await axios.delete(`${API}/clear-history`);
      setHistory([]);
    } catch {
      loadHistory();
    }
  };

  const groupedHistory = groupHistory(history);

  return (
    <div className="info-panel">
      <p className="eyebrow">Memory</p>
      <h3>Chat History</h3>
      <div className="history-actions">
        <button className="secondary-button" type="button" onClick={exportHistory}>
          Export History
        </button>
        <button className="danger-button" type="button" onClick={clearHistory}>
          Clear History
        </button>
      </div>
      {history.length === 0 ? (
        <p className="empty-copy">No conversation history yet.</p>
      ) : (
        Object.entries(groupedHistory).map(
          ([group, items]) =>
            items.length > 0 && (
              <div key={group} className="history-group">
                <h4 className="history-group-title">{group}</h4>
                {items.map((item, index) => (
                  <div key={`${group}-${item.role}-${index}`} className="info-card history-card card">
                    <strong>{item.role}</strong>
                    <span>{item.content}</span>
                    <small className="history-date">
                      {item.timestamp ? new Date(item.timestamp).toLocaleString() : "Date unavailable"}
                    </small>
                  </div>
                ))}
              </div>
            ),
        )
      )}
    </div>
  );
}

export default ChatHistory;
