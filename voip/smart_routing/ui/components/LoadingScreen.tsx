"use client";
import { useEffect, useState } from "react";
import { Phone, CheckCircle, XCircle, Loader, AlertTriangle } from "lucide-react";

interface ServiceState {
  api: boolean;
  asterisk: boolean;
  ngrok: boolean;
  ngrok_url: string;
  ngrok_error?: string;
}

interface Props {
  onReady: () => void;
}

export default function LoadingScreen({ onReady }: Props) {
  const [services, setServices] = useState<ServiceState>({
    api: false,
    asterisk: false,
    ngrok: false,
    ngrok_url: "",
  });
  const [ngrokStarting, setNgrokStarting] = useState(false);
  const [ngrokAttempts, setNgrokAttempts] = useState(0);
  const [dots, setDots] = useState(".");

  useEffect(() => {
    const t = setInterval(() => setDots((d) => (d.length >= 3 ? "." : d + ".")), 500);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      try {
        const r = await fetch("http://localhost:5000/api/services/status", {
          signal: AbortSignal.timeout(3000),
        });
        if (r.ok) {
          const data = await r.json();
          if (!cancelled) {
            setServices((prev) => ({
              ...prev,
              api: true,
              asterisk: data.asterisk,
              ngrok: data.ngrok,
              ngrok_url: data.ngrok_url || prev.ngrok_url,
            }));

            // Auto-start ngrok if not running and haven't tried too many times
            if (!data.ngrok && !ngrokStarting && ngrokAttempts < 2) {
              setNgrokStarting(true);
              setNgrokAttempts((n) => n + 1);
              try {
                const nr = await fetch("http://localhost:5000/api/services/start-ngrok", {
                  method: "POST",
                  signal: AbortSignal.timeout(15000),
                });
                const nd = await nr.json();
                if (!cancelled) {
                  if (nd.ok) {
                    setServices((prev) => ({ ...prev, ngrok: true, ngrok_url: nd.url }));
                  } else {
                    setServices((prev) => ({ ...prev, ngrok_error: nd.error }));
                  }
                  setNgrokStarting(false);
                }
              } catch {
                if (!cancelled) setNgrokStarting(false);
              }
            }
          }
        }
      } catch {
        // API not ready yet
      }
    };

    poll();
    const interval = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [ngrokStarting, ngrokAttempts]);

  // Ready when API + Asterisk are up (Ngrok is optional — can be set up later)
  const coreReady = services.api && services.asterisk;
  const allReady  = coreReady && services.ngrok;
  const ngrokFailed = ngrokAttempts >= 2 && !services.ngrok;

  useEffect(() => {
    if (allReady) {
      const t = setTimeout(onReady, 800);
      return () => clearTimeout(t);
    }
  }, [allReady, onReady]);

  const progress = [services.api, services.asterisk, services.ngrok].filter(Boolean).length;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "#1a1a2e",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
    >
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 40 }}>
        <div style={{
          width: 56, height: 56, borderRadius: "50%", background: "#e94560",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Phone size={28} color="#fff" />
        </div>
        <div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#fff", letterSpacing: 2 }}>
            SMART DIALER
          </div>
          <div style={{ fontSize: 12, color: "#636e72", letterSpacing: 3 }}>
            OUTBOUND CALL CENTER
          </div>
        </div>
      </div>

      {/* Service checklist */}
      <div style={{
        background: "#16213e", border: "1px solid #2d3436", borderRadius: 10,
        padding: "28px 40px", minWidth: 360, display: "flex", flexDirection: "column", gap: 18,
      }}>
        <div style={{ fontSize: 11, color: "#636e72", letterSpacing: 2, textTransform: "uppercase", marginBottom: 4 }}>
          Starting Services
        </div>

        <ServiceRow
          label="API Backend"
          status={services.api ? "ok" : "loading"}
          detail={services.api ? "Running on port 5000" : `Connecting${dots}`}
        />

        <ServiceRow
          label="Asterisk PBX"
          status={services.asterisk ? "ok" : services.api ? "loading" : "waiting"}
          detail={
            services.asterisk ? "Running in WSL2" :
            services.api ? `Starting${dots}` : "Waiting for API..."
          }
        />

        <ServiceRow
          label="Ngrok Tunnel"
          status={
            services.ngrok ? "ok" :
            ngrokFailed ? "error" :
            ngrokStarting ? "loading" :
            services.api ? "loading" : "waiting"
          }
          detail={
            services.ngrok    ? services.ngrok_url :
            ngrokFailed       ? "Not found — skip or add ngrok.exe to folder" :
            ngrokStarting     ? `Starting tunnel${dots}` :
            services.api      ? `Detecting${dots}` : "Waiting..."
          }
        />
      </div>

      {/* Progress bar */}
      <div style={{ marginTop: 20, width: 360, height: 3, background: "#2d3436", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%",
          background: allReady ? "#00b894" : "#e94560",
          width: `${(progress / 3) * 100}%`,
          transition: "width 0.5s ease",
          borderRadius: 2,
        }} />
      </div>

      {/* Status message */}
      <div style={{ marginTop: 16, fontSize: 13, color: allReady ? "#00b894" : "#636e72" }}>
        {allReady ? "All systems ready — launching dashboard..." : `Initializing${dots}`}
      </div>

      {/* Ngrok failed — show skip button */}
      {ngrokFailed && coreReady && (
        <div style={{ marginTop: 20, display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
          <div style={{
            background: "rgba(253,203,110,0.1)", border: "1px solid rgba(253,203,110,0.3)",
            borderRadius: 6, padding: "10px 16px", maxWidth: 380, fontSize: 11,
            color: "#fdcb6e", textAlign: "center",
          }}>
            <AlertTriangle size={13} style={{ display: "inline", marginRight: 6 }} />
            Ngrok not found. Place <strong>ngrok.exe</strong> in the Smart Dialer folder and restart.
            Calls will not work without it.
          </div>
          <button
            onClick={onReady}
            style={{
              background: "#0984e3", color: "#fff", border: "none", borderRadius: 4,
              padding: "8px 24px", fontSize: 12, fontWeight: 700, cursor: "pointer",
              letterSpacing: 0.5,
            }}
          >
            Continue Anyway (Ngrok Missing)
          </button>
        </div>
      )}
    </div>
  );
}

function ServiceRow({ label, status, detail }: {
  label: string;
  status: "ok" | "loading" | "error" | "waiting";
  detail: string;
}) {
  const icon =
    status === "ok"      ? <CheckCircle size={18} color="#00b894" /> :
    status === "error"   ? <XCircle size={18} color="#d63031" /> :
    status === "loading" ? (
      <Loader size={18} color="#0984e3" style={{ animation: "spin 1s linear infinite" }} />
    ) : (
      <div style={{ width: 18, height: 18, borderRadius: "50%", background: "#2d3436" }} />
    );

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{ flexShrink: 0 }}>{icon}</div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#fff" }}>{label}</div>
        <div style={{
          fontSize: 10, marginTop: 1, wordBreak: "break-all",
          color: status === "ok" ? "#00b894" : status === "error" ? "#d63031" : "#636e72",
        }}>
          {detail}
        </div>
      </div>
    </div>
  );
}
