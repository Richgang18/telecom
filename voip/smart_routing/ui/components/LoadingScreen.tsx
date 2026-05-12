"use client";
import { useEffect, useState } from "react";
import { Phone, CheckCircle, XCircle, Loader } from "lucide-react";

interface Props {
  onReady: () => void;
}

export default function LoadingScreen({ onReady }: Props) {
  const [apiOk, setApiOk]         = useState(false);
  const [asteriskOk, setAsteriskOk] = useState(false);
  const [ngrokOk, setNgrokOk]     = useState(false);
  const [ngrokUrl, setNgrokUrl]   = useState("");
  const [ngrokErr, setNgrokErr]   = useState("");
  const [dots, setDots]           = useState(".");
  const [elapsed, setElapsed]     = useState(0);

  // Animate dots
  useEffect(() => {
    const t = setInterval(() => setDots((d) => (d.length >= 3 ? "." : d + ".")), 500);
    return () => clearInterval(t);
  }, []);

  // Count elapsed seconds
  useEffect(() => {
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // Auto-proceed after 15s no matter what
  useEffect(() => {
    if (elapsed >= 15) onReady();
  }, [elapsed, onReady]);

  // Poll API
  useEffect(() => {
    let cancelled = false;
    let ngrokStarted = false;

    const poll = async () => {
      try {
        const r = await fetch("http://localhost:5000/api/services/status", {
          signal: AbortSignal.timeout(2000),
        });
        if (!r.ok) return;
        const d = await r.json();
        if (cancelled) return;

        setApiOk(true);
        setAsteriskOk(!!d.asterisk);

        if (d.ngrok) {
          setNgrokOk(true);
          setNgrokUrl(d.ngrok_url || "");
        } else if (!ngrokStarted) {
          ngrokStarted = true;
          // Try to start ngrok
          fetch("http://localhost:5000/api/services/start-ngrok", {
            method: "POST",
            signal: AbortSignal.timeout(15000),
          })
            .then((r) => r.json())
            .then((nd) => {
              if (cancelled) return;
              if (nd.ok) {
                setNgrokOk(true);
                setNgrokUrl(nd.url || "");
              } else {
                setNgrokErr(nd.error || "Ngrok failed");
              }
            })
            .catch(() => setNgrokErr("Ngrok not available"));
        }
      } catch {
        // API not ready yet
      }
    };

    poll();
    const iv = setInterval(poll, 2000);
    return () => { cancelled = true; clearInterval(iv); };
  }, []);

  // Proceed when API + Asterisk ready (ngrok optional)
  useEffect(() => {
    if (apiOk && asteriskOk && ngrokOk) {
      setTimeout(onReady, 600);
    }
  }, [apiOk, asteriskOk, ngrokOk, onReady]);

  const progress = [apiOk, asteriskOk, ngrokOk].filter(Boolean).length;

  return (
    <div style={{
      position: "fixed", inset: 0, background: "#1a1a2e",
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", zIndex: 9999,
    }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 40 }}>
        <div style={{
          width: 56, height: 56, borderRadius: "50%", background: "#e94560",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Phone size={28} color="#fff" />
        </div>
        <div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#fff", letterSpacing: 2 }}>SMART DIALER</div>
          <div style={{ fontSize: 12, color: "#636e72", letterSpacing: 3 }}>OUTBOUND CALL CENTER</div>
        </div>
      </div>

      {/* Checklist */}
      <div style={{
        background: "#16213e", border: "1px solid #2d3436", borderRadius: 10,
        padding: "28px 40px", minWidth: 360, display: "flex", flexDirection: "column", gap: 18,
      }}>
        <div style={{ fontSize: 11, color: "#636e72", letterSpacing: 2, textTransform: "uppercase" }}>
          Starting Services
        </div>

        <Row label="API Backend"  ok={apiOk}      loading={!apiOk}           detail={apiOk ? "Running on port 5000" : `Connecting${dots}`} />
        <Row label="Asterisk PBX" ok={asteriskOk} loading={apiOk && !asteriskOk} detail={asteriskOk ? "Running in WSL2" : apiOk ? `Starting${dots}` : "Waiting..."} />
        <Row label="Ngrok Tunnel" ok={ngrokOk}    loading={apiOk && !ngrokOk && !ngrokErr}
          error={!!ngrokErr}
          detail={ngrokOk ? ngrokUrl : ngrokErr || (apiOk ? `Starting${dots}` : "Waiting...")} />
      </div>

      {/* Progress bar */}
      <div style={{ marginTop: 20, width: 360, height: 3, background: "#2d3436", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%", background: "#e94560",
          width: `${(progress / 3) * 100}%`,
          transition: "width 0.5s ease", borderRadius: 2,
        }} />
      </div>

      {/* Status + timer */}
      <div style={{ marginTop: 14, fontSize: 12, color: "#636e72" }}>
        {elapsed < 15
          ? `Initializing${dots} (auto-launching in ${15 - elapsed}s)`
          : "Launching dashboard..."}
      </div>

      {/* Manual skip */}
      {elapsed >= 5 && (
        <button
          onClick={onReady}
          style={{
            marginTop: 16, background: "transparent", border: "1px solid #2d3436",
            color: "#636e72", borderRadius: 4, padding: "6px 20px",
            fontSize: 11, cursor: "pointer",
          }}
        >
          Skip &rarr; Open Dashboard
        </button>
      )}
    </div>
  );
}

function Row({ label, ok, loading, error, detail }: {
  label: string; ok: boolean; loading: boolean; error?: boolean; detail: string;
}) {
  const icon = ok
    ? <CheckCircle size={18} color="#00b894" />
    : error
    ? <XCircle size={18} color="#d63031" />
    : loading
    ? <Loader size={18} color="#0984e3" style={{ animation: "spin 1s linear infinite" }} />
    : <div style={{ width: 18, height: 18, borderRadius: "50%", background: "#2d3436" }} />;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
      <div style={{ flexShrink: 0 }}>{icon}</div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: "#fff" }}>{label}</div>
        <div style={{
          fontSize: 10, marginTop: 1, wordBreak: "break-all",
          color: ok ? "#00b894" : error ? "#d63031" : "#636e72",
        }}>{detail}</div>
      </div>
    </div>
  );
}
