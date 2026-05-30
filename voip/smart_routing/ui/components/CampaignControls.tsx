"use client";
import { useDialerStore } from "@/lib/store";
import { startDialer, stopDialer, detectNgrok } from "@/lib/api";
import { Play, Square, Zap, AlertTriangle } from "lucide-react";
import { useState } from "react";

export default function CampaignControls() {
  const { system, setSystem, addLog } = useDialerStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleStart = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await startDialer();
      if (r.ok) {
        setSystem({ dialer_running: true });
        addLog({ id: Date.now().toString(), ts: new Date().toISOString(), event: "dialer_started" });
      } else {
        setError(r.error || "Failed to start dialer");
      }
    } catch (e: any) {
      setError("API not reachable — is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    setError(null);
    try {
      await stopDialer();
      setSystem({ dialer_running: false });
      addLog({ id: Date.now().toString(), ts: new Date().toISOString(), event: "dialer_stopped" });
    } finally {
      setLoading(false);
    }
  };

  const handleDetectNgrok = async () => {
    setError(null);
    const r = await detectNgrok();
    if (r.ok) {
      setSystem({ ngrok: true, ngrok_url: r.url });
      addLog({ id: Date.now().toString(), ts: new Date().toISOString(), event: "log", msg: `Ngrok URL updated: ${r.url}` });
    } else {
      setError("Ngrok not detected. Make sure it is running, then click Detect Ngrok again.");
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
          {loading && !system.dialer_running ? "Starting..." : "Start Campaign"}
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
          disabled={loading}
        >
          <Zap size={12} />
          Detect Ngrok
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div
          style={{
            marginTop: 10,
            display: "flex",
            alignItems: "flex-start",
            gap: 6,
            fontSize: 11,
            color: "#d63031",
            background: "rgba(214,48,49,0.08)",
            border: "1px solid rgba(214,48,49,0.25)",
            borderRadius: 4,
            padding: "7px 10px",
          }}
        >
          <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>{error}</span>
        </div>
      )}

      {system.ngrok_url && !error && (
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
