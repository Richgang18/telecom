"use client";
import { useDialerStore } from "@/lib/store";
import { startDialer, stopDialer, detectNgrok } from "@/lib/api";
import { Play, Square, RefreshCw, Zap } from "lucide-react";
import { useState } from "react";

export default function CampaignControls() {
  const { system, setSystem, addLog } = useDialerStore();
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    setLoading(true);
    try {
      const r = await startDialer();
      if (r.ok) {
        setSystem({ dialer_running: true });
        addLog({ id: Date.now().toString(), ts: new Date().toISOString(), event: "dialer_started" });
      } else {
        alert(r.error || "Failed to start dialer");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopDialer();
      setSystem({ dialer_running: false });
      addLog({ id: Date.now().toString(), ts: new Date().toISOString(), event: "dialer_stopped" });
    } finally {
      setLoading(false);
    }
  };

  const handleDetectNgrok = async () => {
    const r = await detectNgrok();
    if (r.ok) {
      setSystem({ ngrok: true, ngrok_url: r.url });
      addLog({ id: Date.now().toString(), ts: new Date().toISOString(), event: "log", msg: `Ngrok URL: ${r.url}` });
    } else {
      alert("Ngrok not detected. Make sure it is running.");
    }
  };

  return (
    <div className="vici-card">
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          color: "#636e72",
          letterSpacing: 1,
          textTransform: "uppercase",
          marginBottom: 12,
        }}
      >
        Campaign Controls
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button
          className="vici-btn vici-btn-green"
          onClick={handleStart}
          disabled={system.dialer_running || loading}
        >
          <Play size={12} />
          Start Campaign
        </button>

        <button
          className="vici-btn vici-btn-red"
          onClick={handleStop}
          disabled={!system.dialer_running || loading}
        >
          <Square size={12} />
          Stop Campaign
        </button>

        <button
          className="vici-btn vici-btn-blue"
          onClick={handleDetectNgrok}
        >
          <Zap size={12} />
          Detect Ngrok
        </button>
      </div>

      {system.ngrok_url && (
        <div
          style={{
            marginTop: 10,
            fontSize: 10,
            color: "#00b894",
            background: "rgba(0,184,148,0.08)",
            border: "1px solid rgba(0,184,148,0.2)",
            borderRadius: 4,
            padding: "5px 8px",
            wordBreak: "break-all",
          }}
        >
          🌐 {system.ngrok_url}
        </div>
      )}

      {system.dialer_running && (
        <div
          style={{
            marginTop: 10,
            display: "flex",
            alignItems: "center",
            gap: 6,
            fontSize: 11,
            color: "#00b894",
          }}
        >
          <span className="status-dot green pulse" />
          Campaign is running...
        </div>
      )}
    </div>
  );
}
