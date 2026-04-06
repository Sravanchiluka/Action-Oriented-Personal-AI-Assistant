import React from "react";
import Particles from "react-tsparticles";

const actions = [
  { label: "Chat", icon: "Chat", page: "chat" },
  { label: "Notes", icon: "Notes", page: "notes" },
  { label: "Reminders", icon: "Alarm", page: "reminders" },
  { label: "Event Scheduler", icon: "Plan", page: "calendar" },
  { label: "Document Summarizer", icon: "Docs", page: "documents" },
];

function Dashboard({ setPage }) {
  return (
    <div className="dashboard-shell">
      <Particles
        className="dashboard-particles"
        options={{
          fullScreen: false,
          fpsLimit: 60,
          particles: {
            number: { value: 60 },
            size: { value: { min: 1, max: 3 } },
            move: { speed: 0.3 },
            color: { value: "#58d0ff" },
            opacity: { value: 0.6 },
            links: {
              enable: true,
              color: "#3b82f6",
              opacity: 0.2,
              distance: 130,
            },
          },
          interactivity: {
            events: {
              onHover: {
                enable: true,
                mode: "grab",
              },
            },
            modes: {
              grab: {
                distance: 140,
                links: {
                  opacity: 0.35,
                },
              },
            },
          },
        }}
      />

      <div className="dashboard-hero">
        <div className="ai-core glow">
          <div className="ring ring1" />
          <div className="ring ring2" />
          <div className="ring ring3" />
          <div className="core-glow" />
          <div className="robot">AI</div>
        </div>

        <div className="dashboard-copy">
          <p className="eyebrow">Neural Command Surface</p>
          <h1>AI Control Center</h1>
          <p>
            Chat, search, remember, summarize, and stay on top of reminders from one live assistant panel.
          </p>
        </div>
      </div>

      <div className="dashboard-grid">
        {actions.map((action) => (
          <button
            key={action.label}
            className="dashboard-card card"
            onClick={() => setPage(action.page)}
            type="button"
          >
            <span className="dashboard-card-icon">{action.icon}</span>
            <span>{action.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;
