"use client";
import { useDialerStore } from "@/lib/store";
import { Phone, PhoneOff, User } from "lucide-react";

export default function AgentPanel() {
  const { agents } = useDialerStore();

  return (
    <div className="vici-card">
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          color: "#636e72",
          letterSpacing: 1,
          textTransform: "uppercase",
          marginBottom: 10,
        }}
      >
        Agent Status
      </div>

      {agents.length === 0 && (
        <div style={{ color: "#636e72", fontSize: 11, textAlign: "center", padding: "12px 0" }}>
          No agents configured
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {agents.map((agent) => (
          <div
            key={agent.id}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              background: "#0d1b2a",
              borderRadius: 4,
              padding: "8px 12px",
              border: `1px solid ${agent.status === "available" ? "#00b894" : agent.status === "busy" ? "#e94560" : "#2d3436"}`,
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: agent.status === "available" ? "#00b894" : agent.status === "busy" ? "#e94560" : "#636e72",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <User size={14} color="#fff" />
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 12, color: "#fff" }}>
                {agent.name}
              </div>
              {agent.mobile && (
                <div style={{ fontSize: 10, color: "#636e72" }}>{agent.mobile}</div>
              )}
            </div>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                fontSize: 10,
                fontWeight: 700,
                color:
                  agent.status === "available" ? "#00b894" :
                  agent.status === "busy" ? "#e94560" : "#636e72",
              }}
            >
              {agent.status === "busy" ? (
                <Phone size={11} className="pulse" />
              ) : (
                <PhoneOff size={11} />
              )}
              {agent.status.toUpperCase()}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
