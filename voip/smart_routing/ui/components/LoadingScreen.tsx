"use client";
import { useEffect, useState } from "react";
import { Phone, CheckCircle, XCircle, Loader } from "lucide-react";

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
  const [dots, setDots] = useState(".");

  // Animate dots
  useEffect(() => {
    const t = setInterval(() => setDots((d) => (d.length >= 3 ? "." : d + ".")), 500);
    return () => clearInterval(t);
  }, []);

  // Poll services every 2s
  useEffect(() => {
    let cancelled = false;

    const poll = async () => {
      // Step 1: Check API
      try {
        const r = await fetch("http://localhost:5000/api/services/status", { signal: AbortSignal.timeout(3000) });
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

            // Auto-start ngrok if not running
            if (!data.ngrok && !ngrokStarting) {
              setNgrokStarting(true);
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
  }, [ngrokStarting]);

  // All ready → show main UI
  useEffect(() => {
    if (services.api && services.asterisk && services.ngrok) {
      const t = setTimeout(onReady, 800);
      return () => clearTimeout(t);
    }
  }, [services, onReady]);

  const allReady = services.api && services.asterisk && services.ngrok;

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
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 48 }}>
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            background: "#e94560",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
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
      <div
        style={{
          background: "#16213e",
          border: "1px solid #2d3436",
          borderRadius: 10,
          padding: "28px 40px",
          minWidth: 340,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
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
            services.asterisk
              ? "Running in WSL2"
              : services.api
              ? `Starting${dots}`
              : "Waiting for API..."
          }
        />

        <ServiceRow
          label="Ngrok Tunnel"
          status={
            services.ngrok ? "ok" :
            services.ngrok_error ? "error" :
            ngrokStarting ? "loading" :
            services.api ? "loading" : "waiting"
          }
          detail={
            services.ngrok
              ? services.ngrok_url
              : services.ngrok_error
              ? services.ngrok_error
              : ngrokStarting
              ? `Starting tunnel${dots}`
              : services.api
              ? `Detecting${dots}`
              : "Waiting..."
          }
        />
      </div>

      {/* Status message */}
      <div style={{ marginTop: 28, fontSize: 13, color: allReady ? "#00b894" : "#636e72" }}>
        {allReady
          ? "✓ All systems ready — launching dashboard..."
          : `Initializing${dots}`}
      </div>

      {/* Progress bar */}
      <div
        style={{
          marginTop: 16,
          width: 340,
          height: 3,
          background: "#2d3436",
          borderRadius: 2,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            background: allReady ? "#00b894" : "#e94560",
            width: `${
              ([services.api, services.asterisk, services.ngrok].filter(Boolean).length / 3) * 100
            }%`,
            transition: "width 0.5s ease",
            borderRadius: 2,
          }}
        />
      </div>

      {/* Ngrok error help */}
      {services.ngrok_error && (
        <div
          style={{
            marginTop: 20,
            background: "rgba(214,48,49,0.1)",
            border: "1px solid rgba(214,48,49,0.3)",
            borderRadius: 6,
            padding: "12px 16px",
            maxWidth: 400,
            fontSize: 11,
            color: "#ff7675",
            textAlign: "center",
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 4 }}>⚠ Ngrok not found</div>
          <div>Download ngrok.exe from ngrok.com and place it in the Smart Dialer folder, then restart.</div>
        </div>
      )}
    </div>
  );
}

function ServiceRow({
  label,
  status,
  detail,
}: {
  label: string;
  status: "ok" | "loading" | "error" | "waiting";
  detail: string;
}) {
  const icon =
    status === "ok" ? <CheckCircle size={18} color="#00b894" /> :
    status === "error" ? <XCircle size={18} color="#d63031" /> :
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
        <div
          style={{
            fontSize: 10,
            color: status === "ok" ? "#00b894" : status === "error" ? "#d63031" : "#636e72",
            marginTop: 1,
            wordBreak: "break-all",
          }}
        >
          {detail}
        </div>
      </div>
    </div>
  );
}
