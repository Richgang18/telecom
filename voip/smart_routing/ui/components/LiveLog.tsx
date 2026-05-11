"use client";
import { useDialerStore } from "@/lib/store";
import { useEffect, useRef } from "react";

const EVENT_COLOR: Record<string, string> = {
  log:            "#dfe6e9",
  call_connected: "#00b894",
  no_answer:      "#fdcb6e",
  amd_machine:    "#e17055",
  agent_available:"#74b9ff",
  dialer_started: "#00b894",
  dialer_stopped: "#d63031",
  no_agent:       "#e17055",
  init:           "#636e72",
};

export default function LiveLog() {
  const { callLog } = useDialerStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [callLog]);

  return (
    <div
      className="vici-card"
      style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}
    >
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          color: "#636e72",
          letterSpacing: 1,
          textTransform: "uppercase",
          marginBottom: 8,
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <span>Live Activity Log</span>
        <span style={{ color: "#0984e3" }}>{callLog.length} events</span>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          fontFamily: "monospace",
          fontSize: 11,
          lineHeight: 1.6,
          background: "#0d1b2a",
          borderRadius: 4,
          padding: "8px 10px",
        }}
      >
        {callLog.length === 0 && (
          <div style={{ color: "#636e72", textAlign: "center", paddingTop: 20 }}>
            Waiting for activity...
          </div>
        )}
        {[...callLog].reverse().map((entry) => (
          <div
            key={entry.id}
            className="slide-in"
            style={{ color: EVENT_COLOR[entry.event] || "#dfe6e9", marginBottom: 2 }}
          >
            <span style={{ color: "#636e72" }}>
              {new Date(entry.ts).toLocaleTimeString()}
            </span>{" "}
            <span style={{ color: "#74b9ff", fontWeight: 600 }}>
              [{entry.event.toUpperCase()}]
            </span>{" "}
            {entry.msg || formatEvent(entry)}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function formatEvent(e: any): string {
  if (e.event === "call_connected") return `Call ${e.call_sid?.slice(-6)} → Agent ${e.agent} ${e.mobile ? `(${e.mobile})` : ""}`;
  if (e.event === "no_answer")      return `No answer: ${e.to} (${e.status})`;
  if (e.event === "amd_machine")    return `AMD: machine detected on ${e.call_sid?.slice(-6)}`;
  if (e.event === "agent_available")return `Agent ${e.agent} is now available`;
  if (e.event === "dialer_started") return "Dialer campaign started";
  if (e.event === "dialer_stopped") return "Dialer campaign stopped";
  if (e.event === "no_agent")       return "No agents available — call queued";
  return JSON.stringify(e);
}
