import React from "react";
import { motion } from "framer-motion";

const orbitButtons = [
  { label: "Chat", icon: "Chat", page: "chat", angle: 0 },
  { label: "Notes", icon: "Notes", page: "notes", angle: 60 },
  { label: "Reminders", icon: "Alarm", page: "reminders", angle: 120 },
  { label: "Event Scheduler", icon: "Plan", page: "calendar", angle: 180 },
  { label: "Document Summarizer", icon: "Docs", page: "documents", angle: 240 },
  { label: "Search", icon: "Find", page: "chat", angle: 300 },
];

function AIDashboard({ setPage }) {
  const radius = 160;

  return (
    <div
      style={{
        height: "100%",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        position: "relative",
      }}
    >
      <motion.div
        animate={{ rotate: [0, 10, -10, 0] }}
        transition={{ repeat: Infinity, duration: 4 }}
        style={{
          width: "130px",
          height: "130px",
          borderRadius: "50%",
          background: "linear-gradient(135deg,#3b82f6,#06b6d4)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "40px",
          fontWeight: 700,
          boxShadow: "0 0 30px #3b82f6",
          zIndex: 2,
          color: "white",
        }}
      >
        AI
      </motion.div>

      {orbitButtons.map((btn, i) => {
        const rad = (btn.angle * Math.PI) / 180;
        const x = radius * Math.cos(rad);
        const y = radius * Math.sin(rad);

        return (
          <motion.div
            key={i}
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 30, ease: "linear" }}
            style={{
              position: "absolute",
              transform: `translate(${x}px, ${y}px)`,
            }}
          >
            <motion.div
              whileHover={{ scale: 1.2 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setPage(btn.page)}
              style={{
                width: "80px",
                height: "80px",
                borderRadius: "50%",
                background: "#1e293b",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexDirection: "column",
                cursor: "pointer",
                border: "2px solid #3b82f6",
                color: "white",
                fontSize: "16px",
                fontWeight: 700,
                boxShadow: "0 0 15px #3b82f6",
                textAlign: "center",
                padding: "8px",
              }}
            >
              {btn.icon}
              <div style={{ fontSize: "11px", marginTop: "3px" }}>
                {btn.label}
              </div>
            </motion.div>
          </motion.div>
        );
      })}
    </div>
  );
}

export default AIDashboard;
