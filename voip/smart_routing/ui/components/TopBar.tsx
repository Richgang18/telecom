"use client";
import { useEffect } from "react";
import { useDialerStore } from "@/lib/store";
import { Phone, Wifi, WifiOff } from "lucide-react";

export default function TopBar() {
  const { wsConnected, system, setSystem } = useDialerStore();

  // Poll service status every 10s to keep top bar accurate
  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch("http://localhost:5000/api/services/status");
        if (r.ok) {
          const d = await r.json();
          setSystem({
            asterisk: d.asterisk,
            ngrok: d.ngrok,
            ngrok_url: d.ngrok_url || "",
            webhook: true,
          });
        }
      } catch {
        setSystem({ webhook: false });
      }
    };
    check();
    const t = setInterval(check, 10000);
    return () => clearInterval(t);
  }, [setSystem]);

  return (
    <header
      style={{
        background: "#0f3460",
        borderBottom: "2px solid #e94560",
        padding: "0 16px",
        height: 44,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Phone size={18} color="#e94560" />
        <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: 1, color: "#fff" }}>
          SMART DIALER
        </span>
        <span
          style={{
            background: "#e94560",
            color: "#fff",
            fontSize: 9,
            fontWeight: 700,
            padding: "2px 6px",
            borderRadius: 3,
            letterSpacing: 1,
          }}
        >
          PRO
        </span>
      </div>

      {/* Status pills */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <StatusPill label="ASTERISK" active={system.asterisk} />
        <StatusPill label="API"      active={system.webhook} />
        <StatusPill label="NGROK"    active={system.ngrok} />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 5,
            fontSize: 11,
            color: wsConnected ? "#00b894" : "#636e72",
          }}
        >
          {wsConnected ? <Wifi size={13} /> : <WifiOff size={13} />}
          {wsConnected ? "LIVE" : "OFFLINE"}
        </div>
      </div>
    </header>
  );
}

function StatusPill({ label, active }: { label: string; active: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 5,
        background: active ? "rgba(0,184,148,0.15)" : "rgba(99,110,114,0.15)",
        border: `1px solid ${active ? "#00b894" : "#636e72"}`,
        borderRadius: 3,
        padding: "2px 8px",
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: 0.5,
        color: active ? "#00b894" : "#636e72",
      }}
    >
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: active ? "#00b894" : "#636e72",
          boxShadow: active ? "0 0 6px #00b894" : "none",
          display: "inline-block",
          flexShrink: 0,
        }}
      />
      {label}
    </div>
  );
}
