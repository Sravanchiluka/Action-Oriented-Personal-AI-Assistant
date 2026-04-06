import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";

import "./Chat.css";
import ActivityTimeline from "./components/ActivityTimeline";
import ChatHistory from "./components/ChatHistory";
import Dashboard from "./components/Dashboard";

const API = "http://127.0.0.1:8000";
const pages = [
  { text: "Dashboard", page: "dashboard" },
  { text: "Chat", page: "chat" },
  { text: "Notes", page: "notes" },
  { text: "Reminders", page: "reminders" },
  { text: "Event Scheduler", page: "calendar" },
  { text: "Email Automation", page: "email" },
  { text: "Document Summarizer", page: "documents" },
  { text: "History", page: "history" },
  { text: "Timeline", page: "timeline" },
];

function createMessage(role, text, extra = {}) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    role,
    text,
    ...extra,
  };
}

function Chat({ theme, toggleTheme }) {
  const [page, setPage] = useState("dashboard");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [notes, setNotes] = useState([]);
  const [reminders, setReminders] = useState([]);
  const [calendar, setCalendar] = useState([]);
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [searchHistory, setSearchHistory] = useState([]);
  const [voiceConversationMode, setVoiceConversationMode] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [showAllReminders, setShowAllReminders] = useState(false);
  const [, setReminderTick] = useState(0);

  const removeNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const speakingTimerRef = useRef(null);
  const recognitionRef = useRef(null);
  const speechSynthesisRef = useRef(null);
  const lastSpokenRef = useRef("");
  const voiceModeRef = useRef(false);
  const activeRecognitionModeRef = useRef("idle");
  const pageTitle =
    page === "documents"
      ? "Document Summarizer"
      : page === "calendar"
        ? "Event Scheduler"
        : page.charAt(0).toUpperCase() + page.slice(1);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    console.log("Messages updated:", messages);
  }, [messages]);

  useEffect(() => {
    if (page === "notes") {
      fetchNotes();
    }

    if (page === "reminders") {
      fetchReminders();
    }

    if (page === "calendar") {
      fetchCalendar();
    }

    if (page === "search-history") {
      fetchSearchHistory();
    }
  }, [page]);

  useEffect(() => {
    voiceModeRef.current = voiceConversationMode;
  }, [voiceConversationMode]);

  useEffect(() => {
    speechSynthesisRef.current = typeof window !== "undefined" ? window.speechSynthesis : null;
  }, []);

  useEffect(() => {
    const interval = window.setInterval(fetchNotifications, 10000);
    fetchNotifications();

    return () => {
      window.clearInterval(interval);

      if (speakingTimerRef.current) {
        window.clearTimeout(speakingTimerRef.current);
      }

      if (recognitionRef.current) {
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
      }

      speechSynthesisRef.current?.cancel();
    };
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setReminderTick((value) => value + 1);
    }, 1000);

    return () => window.clearInterval(interval);
  }, []);

  const triggerSpeakingAnimation = (text) => {
    if (speakingTimerRef.current) {
      window.clearTimeout(speakingTimerRef.current);
    }

    setSpeaking(true);

    const duration = Math.min(7000, Math.max(1800, (text || "").length * 35));
    speakingTimerRef.current = window.setTimeout(() => setSpeaking(false), duration);
  };

  const speakText = (text) => {
    const synthesis = speechSynthesisRef.current;

    if (!synthesis || typeof window === "undefined" || !("SpeechSynthesisUtterance" in window) || !text?.trim()) {
      return;
    }

    if (lastSpokenRef.current === text) {
      return;
    }

    lastSpokenRef.current = text;

    const utterance = new window.SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;
    utterance.onend = () => setSpeaking(false);

    synthesis.cancel();
    synthesis.speak(utterance);
  };

  const appendAssistantMessage = (text) => {
    setMessages((prev) => {
      return [...prev, createMessage("assistant", text)];
    });
    triggerSpeakingAnimation(text);
  };

  const appendPendingAssistantMessage = (text = "Processing...") => {
    const pendingId = `pending-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setMessages((prev) => {
      return [...prev, { ...createMessage("assistant", text), id: pendingId, pending: true }];
    });
    return pendingId;
  };

  const resolvePendingAssistantMessage = (pendingId, text) => {
    const resolvedText = text || "I couldn't generate a response just now.";
    setMessages((prev) => {
      let updated = false;

      const newMessages = prev.map((message) => {
        if (message.id === pendingId) {
          updated = true;
          return { ...message, text: resolvedText, pending: false };
        }
        return message;
      });

      if (!updated) {
        newMessages.push(createMessage("assistant", resolvedText));
      }

      return [...newMessages];
    });
    triggerSpeakingAnimation(resolvedText);
    speakText(resolvedText);
  };

  const sendMessage = async (text, options = {}) => {
    if (!text.trim()) {
      return;
    }

    const { targetPage = "chat" } = options;

    setPage(targetPage);
    setMessages((prev) => [...prev, createMessage("user", text)]);
    setMessage("");
    const pendingId = appendPendingAssistantMessage();

    try {
      const response = await axios.post(`${API}/chat`, { text });
      console.log("FULL API DATA:", response.data);
      const reply =
        response.data?.response ||
        response.data?.reply ||
        response.data?.message ||
        "Email sent successfully";
      resolvePendingAssistantMessage(pendingId, reply);

      if (/create note|save note|add note/i.test(text)) {
        fetchNotes();
      }

      if (/remind me/i.test(text)) {
        fetchReminders();
      }

      if (/schedule|add event|set event|meeting|appointment|plan tomorrow/i.test(text)) {
        fetchCalendar();
      }

      if (/search /i.test(text)) {
        fetchSearchHistory();
      }
    } catch (error) {
      console.error("Chat request failed:", error);
      if (error.code === "ECONNABORTED") {
        resolvePendingAssistantMessage(pendingId, "Taking longer than expected...");
        return;
      }

      const fallback = error.response?.data?.detail || "Server error";
      resolvePendingAssistantMessage(pendingId, fallback);
    }
  };

  const sendVoiceTranscript = async (transcript) => {
    if (!transcript.trim()) {
      return;
    }

    setPage("chat");
    setMessages((prev) => [...prev, createMessage("user", transcript)]);
    setMessage("");
    const pendingId = appendPendingAssistantMessage();

    try {
      const formData = new FormData();
      formData.append("transcript", transcript);

      const response = await axios.post(`${API}/voice`, formData);
      console.log("FULL API DATA:", response.data);
      const reply =
        response.data?.response ||
        response.data?.reply ||
        response.data?.message ||
        "Email sent successfully";
      resolvePendingAssistantMessage(pendingId, reply);

      if (/search /i.test(transcript)) {
        fetchSearchHistory();
      }

      if (/schedule|add event|set event|meeting|appointment|plan tomorrow/i.test(transcript)) {
        fetchCalendar();
      }
    } catch (error) {
      console.error("Voice request failed:", error);
      if (error.code === "ECONNABORTED") {
        resolvePendingAssistantMessage(pendingId, "Taking longer than expected...");
        return;
      }

      const fallback = error.response?.data?.detail || "Server error";
      resolvePendingAssistantMessage(pendingId, fallback);
    }
  };

  const configureRecognitionForMode = (recognition, mode) => {
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = mode === "voice";
  };

  const createRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      appendAssistantMessage("Speech recognition is not supported in this browser.");
      return null;
    }

    const recognition = new SpeechRecognition();
    configureRecognitionForMode(recognition, "press");

    recognition.onstart = () => {
      setListening(true);
    };
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript?.trim() || "";

      if (!transcript) {
        return;
      }

      if (activeRecognitionModeRef.current === "press") {
        setIsRecording(false);
      }

      setMessage(transcript);
      sendMessage(transcript);
    };
    recognition.onerror = (event) => {
      setListening(false);
      if (activeRecognitionModeRef.current === "press") {
        setIsRecording(false);
      }

      if (event.error === "no-speech" || event.error === "aborted") {
        return;
      }

      if (!voiceModeRef.current) {
        appendAssistantMessage("I could not hear that clearly. Please try again.");
      }
    };
    recognition.onend = () => {
      setListening(false);

      if (activeRecognitionModeRef.current === "press") {
        setIsRecording(false);
      }

      activeRecognitionModeRef.current = "idle";

      if (voiceModeRef.current) {
        setIsRecording(false);
      }
    };

    recognitionRef.current = recognition;
    return recognition;
  };

  const ensureRecognitionMode = (mode) => {
    const recognition = recognitionRef.current || createRecognition();
    if (!recognition) {
      return;
    }

    if (activeRecognitionModeRef.current === mode && listening) {
      return;
    }

    if (activeRecognitionModeRef.current !== "idle") {
      try {
        recognition.stop();
      } catch {
        // Ignore repeated stop attempts while swapping modes.
      }
      return;
    }

    configureRecognitionForMode(recognition, mode);
    activeRecognitionModeRef.current = mode;

    try {
      recognition.start();
    } catch {
      activeRecognitionModeRef.current = "idle";
    }
  };

  const handleMicClick = () => {
    const recognition = recognitionRef.current || createRecognition();
    if (!recognition) {
      return;
    }

    if (isRecording) {
      setIsRecording(false);
      try {
        recognition.stop();
      } catch {
        // Ignore stop races while the browser finalizes recognition.
      }
      return;
    }

    setVoiceConversationMode(false);
    setIsRecording(true);
    ensureRecognitionMode("press");
  };

  const toggleVoiceConversationMode = () => {
    const next = !voiceConversationMode;
    setVoiceConversationMode(next);

    if (!next) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      return;
    }

    ensureRecognitionMode("voice");
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      await axios.post(`${API}/upload`, formData);
      appendAssistantMessage(`Uploaded ${file.name}. Ask me to summarize the document when you're ready.`);
      setPage("documents");
    } catch {
      appendAssistantMessage("Upload failed.");
    } finally {
      event.target.value = "";
    }
  };

  const fetchNotes = async () => {
    try {
      const response = await axios.get(`${API}/notes`);
      setNotes(response.data.items || []);
    } catch {
      setNotes([]);
    }
  };

  const fetchReminders = async () => {
    try {
      const response = await axios.get(`${API}/reminders`);
      setReminders(response.data.items || []);
    } catch {
      setReminders([]);
    }
  };

  const handleClearReminders = async () => {
    try {
      await axios.delete(`${API}/reminders`);
      setReminders([]);
      setShowAllReminders(false);
      appendAssistantMessage("All reminders cleared.");
    } catch {
      appendAssistantMessage("I could not clear the reminders.");
    }
  };

  const handleDeleteReminder = async (index) => {
    try {
      await axios.delete(`${API}/reminders/${index}`);
      fetchReminders();
    } catch {
      appendAssistantMessage("I could not delete that reminder.");
    }
  };

  const handleEditReminder = async (index, reminder) => {
    const newText = window.prompt("Edit reminder text", reminder.text);
    const newTime = window.prompt("Edit time (YYYY-MM-DD HH:MM)", reminder.scheduled_for);

    if (newText === null || newTime === null) {
      return;
    }

    if (!newText.trim() || !newTime.trim()) {
      appendAssistantMessage("Reminder text and time are required.");
      return;
    }

    try {
      await axios.put(`${API}/reminders/${index}`, null, {
        params: {
          text: newText.trim(),
          time: newTime.trim(),
        },
      });
      fetchReminders();
    } catch {
      appendAssistantMessage("I could not update that reminder.");
    }
  };

  const fetchCalendar = async () => {
    try {
      const response = await axios.get(`${API}/calendar`);
      setCalendar(response.data.items || []);
    } catch {
      setCalendar([]);
    }
  };

  const handleDeleteNote = async (index) => {
    try {
      await axios.delete(`${API}/notes/${index}`);
      fetchNotes();
    } catch {
      appendAssistantMessage("I could not delete that note.");
    }
  };

  const handleEditNote = async (index, currentText) => {
    const updatedText = window.prompt("Edit note", currentText);

    if (updatedText === null) {
      return;
    }

    if (!updatedText.trim()) {
      appendAssistantMessage("Note text cannot be empty.");
      return;
    }

    try {
      await axios.put(`${API}/notes/${index}`, null, { params: { text: updatedText.trim() } });
      fetchNotes();
    } catch {
      appendAssistantMessage("I could not update that note.");
    }
  };

  const deleteEvent = async (index) => {
    try {
      await axios.delete(`${API}/calendar/${index}`);
      fetchCalendar();
    } catch {
      appendAssistantMessage("I could not delete that event.");
    }
  };

  const editEvent = async (index, currentText) => {
    const updatedText = window.prompt("Edit event", currentText);

    if (updatedText === null || !updatedText.trim()) {
      return;
    }

    try {
      await axios.put(`${API}/calendar/${index}`, null, { params: { text: updatedText.trim() } });
      fetchCalendar();
    } catch {
      appendAssistantMessage("I could not update that event.");
    }
  };

  const clearAllEvents = async () => {
    try {
      await axios.delete(`${API}/calendar`);
      setCalendar([]);
      appendAssistantMessage("All events cleared.");
    } catch {
      appendAssistantMessage("I could not clear the events.");
    }
  };

  const fetchSearchHistory = async () => {
    try {
      const response = await axios.get(`${API}/search-history`);
      setSearchHistory(response.data.history || []);
    } catch {
      setSearchHistory([]);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await axios.get(`${API}/notifications`);
      const incoming = response.data.notifications || [];

      if (!incoming.length) {
        return;
      }

      setNotifications((current) => [...incoming, ...current].slice(0, 5));

      const newest = incoming[incoming.length - 1];

      if ("Notification" in window && Notification.permission === "granted") {
        incoming.forEach((item) => {
          new Notification(item.title, { body: item.message });
        });
      } else {
        window.alert(`${newest.title}\n${newest.message}`);
      }
    } catch {
      // Keep polling quietly; missing notifications should not break chat.
    }
  };

  const requestBrowserNotifications = async () => {
    if ("Notification" in window && Notification.permission === "default") {
      await Notification.requestPermission();
    }
  };

  const exportChat = () => {
    const text = messages.map((item) => `${item.role.toUpperCase()}: ${item.text}`).join("\n\n");
    const blob = new Blob([text || "No chat messages yet."], { type: "text/plain" });
    const link = document.createElement("a");

    link.href = URL.createObjectURL(blob);
    link.download = "chat_history.txt";
    link.click();

    window.URL.revokeObjectURL(link.href);
  };

  const renderMessage = (msg, index) => {
    const isUser = msg.role === "user";

    return (
      <motion.div
        key={msg.id || index}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className={`message-row ${isUser ? "user" : "assistant"}`}
      >
        <div className={`message-bubble ${isUser ? "user" : "assistant"}`}>
          {(msg.text || "").split("\n").map((line, lineIndex) => (
            <div key={`${index}-${lineIndex}`}>
              {line}
            </div>
          ))}
        </div>
      </motion.div>
    );
  };

  return (
    <div className="assistant-shell">
      <aside className="sidebar">
        <div>
          <p className="sidebar-kicker">AI Personal Assistant</p>
          <h2>Neural Desk</h2>
        </div>

        <div className="sidebar-nav">
          {pages.map((item) => (
            <SidebarButton
              key={item.page}
              text={item.text}
              active={page === item.page}
              onClick={() => setPage(item.page)}
            />
          ))}
        </div>

        <div className="sidebar-footer">
          <button className="notification-button" type="button" onClick={requestBrowserNotifications}>
            Enable reminder alerts
          </button>

          <button className="theme-button" type="button" onClick={toggleTheme}>
            <span aria-hidden="true">{theme === "dark" ? "☀️" : "🌙"}</span>
            <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-title-group">
            <p className="topbar-kicker">Live assistant</p>
            <div className="topbar-title-row">
              <h3>{page === "chat" ? "Conversation" : pageTitle}</h3>
              <div className={`ai-status ${listening ? "active" : ""}`}>
                <span className="ai-status-dot" aria-hidden="true" />
                <span>{listening ? "Listening" : "Mic Ready"}</span>
              </div>
            </div>
          </div>

          <div className="topbar-actions">
            <button className="secondary-button" type="button" onClick={toggleVoiceConversationMode}>
              {voiceConversationMode ? "Stop Voice Mode" : "Voice Mode"}
            </button>
            <button className="secondary-button" type="button" onClick={exportChat}>
              Export Chat
            </button>
          </div>

          <div className="status-cluster">
            <div className="status-pill">Ready</div>
            <div className={`status-pill ${speaking ? "active" : ""}`}>{speaking ? "Speaking" : "Idle"}</div>
            <div className={`status-pill ${voiceConversationMode ? "active" : ""}`}>
              {voiceConversationMode ? "Voice Mode On" : "Voice Mode Off"}
            </div>
          </div>
        </header>

        {notifications.length > 0 && (
          <div className="notification-stack">
            {notifications.map((notification) => (
              <div key={notification.id} className="notification-card">
                <div className="notification-content">
                  <strong>{notification.title}</strong>
                  <span>{notification.message}</span>
                </div>

                <button
                  className="notification-close"
                  onClick={() => removeNotification(notification.id)}
                  aria-label={`Dismiss ${notification.title} notification`}
                >
                  &times;
                </button>
              </div>
            ))}
          </div>
        )}

        <section className="content-panel page-container">
          {page === "dashboard" && <Dashboard setPage={setPage} />}

          {page === "chat" && (
            <div className="chat-panel">
              {messages.length === 0 && (
                <div className="empty-state">
                  <div className="empty-orb">AI</div>
                  <h3>Start a conversation</h3>
                  <p>Ask for notes, reminders, summaries, daily planning, or search help.</p>
                </div>
              )}

              {messages.map(renderMessage)}

              <div ref={chatEndRef} />
            </div>
          )}

          {page === "notes" && <NotesPanel notes={notes} onDelete={handleDeleteNote} onEdit={handleEditNote} />}
          {page === "reminders" && (
            <RemindersPanel
              reminders={reminders}
              showAll={showAllReminders}
              onToggleShowAll={() => setShowAllReminders((value) => !value)}
              onClearAll={handleClearReminders}
              onDelete={handleDeleteReminder}
              onEdit={handleEditReminder}
            />
          )}
          {page === "calendar" && (
            <CalendarPanel
              events={calendar}
              onDelete={deleteEvent}
              onEdit={editEvent}
              onClearAll={clearAllEvents}
            />
          )}
          {page === "email" && <EmailPanel onSend={(text) => sendMessage(text, { targetPage: "email" })} />}
          {page === "search-history" && <InfoPanel title="Search History" items={searchHistory} />}
          {page === "history" && <ChatHistory />}
          {page === "timeline" && <ActivityTimeline />}

          {page === "documents" && (
            <div className="documents-panel">
              <div className="upload-card">
                <p className="eyebrow">Document Summarizer</p>
                <h3>Summarize PDF, TXT, DOCX, or image files</h3>
                <p>The backend can summarize text documents directly and images through OCR when support is installed.</p>
                <button className="primary-button" type="button" onClick={() => fileInputRef.current?.click()}>
                  Choose file
                </button>
              </div>
            </div>
          )}
        </section>

        {isRecording && <div className="listening-box">🎙️ Listening... Speak now</div>}

        <footer className="composer input-container">
          <button className="icon-button" type="button" onClick={() => fileInputRef.current?.click()}>
            +
          </button>

          <input
            type="file"
            ref={fileInputRef}
            className="hidden-input"
            onChange={handleFileUpload}
            accept=".pdf,.txt,.docx,.png,.jpg,.jpeg,.bmp"
          />

          <input
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Ask anything..."
            className="composer-input"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                sendMessage(message);
              }
            }}
          />

          {speaking && (
            <div className="voice-wave" aria-hidden="true">
              <span />
              <span />
              <span />
              <span />
              <span />
            </div>
          )}

          <button
            className={`icon-button mic-btn ${listening ? "listening" : ""} ${isRecording ? "mic-active" : ""}`}
            type="button"
            onClick={handleMicClick}
            aria-label={isRecording ? "Stop recording voice input" : "Start recording voice input"}
          >
            {isRecording ? "🔴" : "🎤"}
          </button>

          <button className="send-button" type="button" onClick={() => sendMessage(message)}>
            ➤
          </button>
        </footer>
      </main>
    </div>
  );
}

function SidebarButton({ text, onClick, active }) {
  return (
    <button className={`sidebar-button ${active ? "active" : ""}`} type="button" onClick={onClick}>
      {text}
    </button>
  );
}

function EmailPanel({ onSend }) {
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");

  const handleSend = () => {
    const recipient = to.trim();
    const body = message.trim();
    const subjectLine = subject.trim();

    if (!recipient || !body) {
      return;
    }

    const subjectText = subjectLine ? ` with subject ${subjectLine}` : "";
    onSend(`send email to ${recipient}${subjectText} ${body}`);
    setMessage("");
  };

  return (
    <div className="info-panel">
      <p className="eyebrow">Email Automation</p>
      <h3>Send Email</h3>
      <p className="empty-copy">Send by form input here, or use voice commands with the same backend flow.</p>

      <input
        placeholder="Recipient Email"
        value={to}
        onChange={(event) => setTo(event.target.value)}
        className="composer-input"
      />

      <input
        placeholder="Subject (optional)"
        value={subject}
        onChange={(event) => setSubject(event.target.value)}
        className="composer-input"
        style={{ marginTop: "10px" }}
      />

      <textarea
        placeholder="Message..."
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        className="composer-input"
        style={{ minHeight: "120px", marginTop: "10px", resize: "vertical" }}
      />

      <div className="panel-actions">
        <button className="primary-button" type="button" onClick={handleSend} disabled={!to.trim() || !message.trim()}>
          Send Email
        </button>
      </div>
    </div>
  );
}

function NotesPanel({ notes, onDelete, onEdit }) {
  return (
    <div className="info-panel">
      <p className="eyebrow">Notes</p>
      <h3>Notes</h3>
      {notes.length === 0 ? (
        <p className="empty-copy">Nothing here yet.</p>
      ) : (
        <div className="notes-grid">
          {notes.map((note, index) => (
            <div key={`note-${index}`} className="note-card">
              <p>{note}</p>
              <div className="card-actions">
                <button className="secondary-button" type="button" onClick={() => onEdit(index, note)}>
                  Edit
                </button>
                <button className="danger-button" type="button" onClick={() => onDelete(index)}>
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RemindersPanel({ reminders, showAll, onToggleShowAll, onClearAll, onDelete, onEdit }) {
  const sortedReminders = reminders
    .map((reminder, index) => ({ reminder, index }))
    .sort((left, right) => new Date(right.reminder.scheduled_for) - new Date(left.reminder.scheduled_for));
  const visibleReminders = showAll ? sortedReminders : sortedReminders.slice(0, 5);
  const groupedReminders = groupReminders(visibleReminders);
  const groupEntries = [
    ["Today", groupedReminders.today],
    ["Tomorrow", groupedReminders.tomorrow],
    ["Later", groupedReminders.later],
  ].filter(([, items]) => items.length > 0);

  return (
    <div className="info-panel">
      <p className="eyebrow">Reminders</p>
      <h3>Reminders</h3>
      {reminders.length === 0 ? (
        <p className="empty-copy">Nothing here yet.</p>
      ) : (
        <>
          <div className="panel-actions">
            <button className="secondary-button" type="button" onClick={onToggleShowAll}>
              {showAll ? "Show Latest 5" : "View All"}
            </button>
            <button className="danger-button" type="button" onClick={onClearAll}>
              Clear All
            </button>
          </div>
          {groupEntries.map(([label, items]) => (
            <div key={label} className="reminder-group">
              <p className="group-label">{label}</p>
              {items.map(({ reminder, index }, itemIndex) => (
                <div key={`${label}-${itemIndex}`} className="reminder-card">
                  <div className="reminder-copy">
                    <strong>{reminder.text}</strong>
                    <span>{reminder.display_time || new Date(reminder.scheduled_for).toLocaleString()}</span>
                  </div>
                  <div className="card-actions">
                    <button className="secondary-button" type="button" onClick={() => onEdit(index, reminder)}>
                      Edit
                    </button>
                    <button className="danger-button" type="button" onClick={() => onDelete(index)}>
                      Delete
                    </button>
                  </div>
                  <div className="countdown-pill">{getRemainingTime(reminder.scheduled_for)}</div>
                </div>
              ))}
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function groupReminders(reminders) {
  const today = [];
  const tomorrow = [];
  const later = [];
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfTomorrow = new Date(startOfToday);
  startOfTomorrow.setDate(startOfTomorrow.getDate() + 1);
  const startOfDayAfterTomorrow = new Date(startOfTomorrow);
  startOfDayAfterTomorrow.setDate(startOfDayAfterTomorrow.getDate() + 1);

  reminders.forEach((entry) => {
    const { reminder } = entry;
    const date = new Date(reminder.scheduled_for);
    if (Number.isNaN(date.getTime())) {
      later.push(entry);
      return;
    }

    if (date >= startOfToday && date < startOfTomorrow) {
      today.push(entry);
      return;
    }

    if (date >= startOfTomorrow && date < startOfDayAfterTomorrow) {
      tomorrow.push(entry);
      return;
    }

    later.push(entry);
  });

  return { today, tomorrow, later };
}

function CalendarPanel({ events, onDelete, onEdit, onClearAll }) {
  const sortedEvents = [...events].sort((left, right) => {
    const leftTime = left?.datetime ? new Date(left.datetime).getTime() : Number.MAX_SAFE_INTEGER;
    const rightTime = right?.datetime ? new Date(right.datetime).getTime() : Number.MAX_SAFE_INTEGER;
    return leftTime - rightTime;
  });
  const groupedEvents = groupCalendarEvents(sortedEvents);
  const groupEntries = [
    ["Today", groupedEvents.today],
    ["Tomorrow", groupedEvents.tomorrow],
    ["Upcoming", groupedEvents.upcoming],
  ].filter(([, items]) => items.length > 0);

  return (
    <div className="info-panel">
      <p className="eyebrow">Event Scheduler</p>
      <h3>Event Scheduler</h3>
      {events.length === 0 ? (
        <p className="empty-copy">Nothing here yet.</p>
      ) : (
        <>
          <div className="panel-actions">
            <button className="danger-button" type="button" onClick={onClearAll}>
              Clear All
            </button>
          </div>

          <div className="calendar-timeline">
            {groupEntries.map(([label, items]) => (
              <div key={label} className="reminder-group">
                <p className="group-label">{label}</p>
                {items.map(({ event, index }) => (
                  <div key={`event-${index}`} className="event-block">
                    <div className="event-time">{formatEventTime(event)}</div>
                    <div className="event-text">
                      <strong>{event.title || event.text}</strong>
                      <span>{event.recurring ? `Repeats ${event.recurring}` : "One-time event"}</span>
                    </div>
                    <div className="countdown-pill">{event.datetime ? getRemainingTime(event.datetime) : "Anytime"}</div>
                    <div className="card-actions">
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => onEdit(index, event.title || event.text)}
                      >
                        Edit
                      </button>
                      <button className="danger-button" type="button" onClick={() => onDelete(index)}>
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function groupCalendarEvents(events) {
  const today = [];
  const tomorrow = [];
  const upcoming = [];
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfTomorrow = new Date(startOfToday);
  startOfTomorrow.setDate(startOfTomorrow.getDate() + 1);
  const startOfDayAfterTomorrow = new Date(startOfTomorrow);
  startOfDayAfterTomorrow.setDate(startOfDayAfterTomorrow.getDate() + 1);

  events.forEach((event, index) => {
    const date = event?.datetime ? new Date(event.datetime) : null;
    const entry = { event, index };

    if (!date || Number.isNaN(date.getTime())) {
      upcoming.push(entry);
      return;
    }

    if (date >= startOfToday && date < startOfTomorrow) {
      today.push(entry);
      return;
    }

    if (date >= startOfTomorrow && date < startOfDayAfterTomorrow) {
      tomorrow.push(entry);
      return;
    }

    upcoming.push(entry);
  });

  return { today, tomorrow, upcoming };
}

function formatEventTime(event) {
  if (event?.datetime) {
    const date = new Date(event.datetime);
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleString([], {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      });
    }
  }

  return event?.time || "Anytime";
}

function getRemainingTime(targetTime) {
  const now = Date.now();
  const target = new Date(targetTime).getTime();
  const diff = target - now;

  if (Number.isNaN(target) || diff <= 0) {
    return "Expired";
  }

  const hours = Math.floor(diff / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);

  if (hours > 0) {
    return `${hours}h ${minutes}m ${seconds}s remaining`;
  }

  return `${minutes}m ${seconds}s remaining`;
}

function InfoPanel({ title, content = "", items = null, preserveSpacing = false }) {
  const derivedItems = items || content.split("\n").filter((item) => item.trim() !== "");

  return (
    <div className="info-panel">
      <p className="eyebrow">{title}</p>
      <h3>{title}</h3>
      {derivedItems.length === 0 ? (
        <p className="empty-copy">Nothing here yet.</p>
      ) : (
        derivedItems.map((item, index) => (
          <div key={`${title}-${index}`} className={`info-card ${preserveSpacing ? "preformatted" : ""}`}>
            {item}
          </div>
        ))
      )}
    </div>
  );
}

export default Chat;
