"use client";
import { useDialerStore } from "@/lib/store";
import { User, Phone, PhoneOff, Clock } from "lucide-react";

export default function Agents() {
  const { agents } = useDialerStore();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="vici-card">
        <div style={{ fontSize: 10, fontWeight: 700, color: "#636e72", letterSpacing: 1, textTransform: "uppercase", marginBottom: 12 }}>
          Agent Overview
        </div>

        {agents.length === 0 ? (
          <div style={{ color: "#636e72", textAlign: "center", padding: "24px 0" }}>
            No agents configured. Add mobile numbers in Settings.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 10 }}>
            {agents.map((agent) => (
              <div
                key={agent.id}
                style={{
                  background: "#0d1b2a",
                  border: `1px solid ${agent.status === "available" ? "#00b894" : agent.status === "busy" ? "#e94560" : "#2d3436"}`,
                  borderRadius: 6,
                  padding: 16,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                  <div
                    style={{
                      width: 44,
                      height: 44,
                      borderRadius: "50%",
                      background: agent.status === "available" ? "#00b894" : agent.status === "busy" ? "#e94560" : "#636e72",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <User size={20} color="#fff" />
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, color: "#fff" }}>{agent.name}</div>
                    <div style={{ fontSize: 10, color: "#636e72" }}>ID: {agent.id}</div>
                  </div>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <Row icon={<Phone size={11} />} label="Mobile" value={agent.mobile || "—"} />
                  <Row
                    icon={agent.status === "busy" ? <Phone size={11} color="#e94560" /> : <PhoneOff size={11} />}
                    label="Status"
                    value={agent.status.toUpperCase()}
                    valueColor={agent.status === "available" ? "#00b894" : agent.status === "busy" ? "#e94560" : "#636e72"}
                  />
                  {agent.call_sid && (
                    <Row icon={<Clock size={11} />} label="Call SID" value={agent.call_sid.slice(-8)} />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ icon, label, value, valueColor = "#dfe6e9" }: any) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11 }}>
      <span style={{ color: "#636e72" }}>{icon}</span>
      <span style={{ color: "#636e72", minWidth: 60 }}>{label}:</span>
      <span style={{ color: valueColor, fontFamily: "monospace" }}>{value}</span>
    </div>
  );
}
