import React from "react";
import { motion } from "framer-motion";
import Particles from "react-tsparticles";

const buttons = [
  { label: "Chat", icon: "Chat", page: "chat", angle: 0 },
  { label: "Notes", icon: "Notes", page: "notes", angle: 72 },
  { label: "Reminders", icon: "Alarm", page: "reminders", angle: 144 },
  { label: "Event Scheduler", icon: "Plan", page: "calendar", angle: 216 },
  { label: "Document Summarizer", icon: "Docs", page: "documents", angle: 288 },
];

function JarvisDashboard({ setPage }) {
  const radius = 200;

  return (
    <div
      style={{
        height: "100%",
        width: "100%",
        position: "relative",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        overflow: "hidden",
      }}
    >
      <Particles
        options={{
          particles: {
            number: { value: 40 },
            size: { value: 2 },
            move: { speed: 0.3 },
            color: { value: "#3b82f6" },
            links: {
              enable: true,
              color: "#3b82f6",
              opacity: 0.3,
            },
          },
        }}
        style={{
          position: "absolute",
          width: "100%",
          height: "100%",
        }}
      />

      <motion.div
        animate={{ rotate: [0, 10, -10, 0] }}
        transition={{ repeat: Infinity, duration: 4 }}
        style={{
          width: "170px",
          height: "170px",
          borderRadius: "50%",
          background: "linear-gradient(135deg,#3b82f6,#06b6d4)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "48px",
          fontWeight: 700,
          boxShadow: "0 0 60px #3b82f6",
          zIndex: 2,
          color: "white",
        }}
      >
        AI
      </motion.div>

      {buttons.map((btn, i) => {
        const rad = (btn.angle * Math.PI) / 180;
        const x = radius * Math.cos(rad);
        const y = radius * Math.sin(rad);

        return (
          <motion.div
            key={i}
            animate={{ rotate: 360 }}
            transition={{
              repeat: Infinity,
              duration: 30,
              ease: "linear",
            }}
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
                width: "90px",
                height: "90px",
                borderRadius: "50%",
                background: "#1e293b",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
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

              <div
                style={{
                  fontSize: "11px",
                  marginTop: "4px",
                }}
              >
                {btn.label}
              </div>
            </motion.div>
          </motion.div>
        );
      })}
    </div>
  );
}

export default JarvisDashboard;
