"use client";
import { useEffect, useState } from "react";
import { fetchConfig, saveConfig } from "@/lib/api";
import { Save, RefreshCw } from "lucide-react";

export default function Settings() {
  const [cfg, setCfg] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchConfig().then(setCfg);
  }, []);

  const update = (section: string, key: string, value: string) => {
    setCfg((prev: any) => ({
      ...prev,
      [section]: { ...prev[section], [key]: value },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await saveConfig({
        twilio: {
          account_sid: cfg.twilio.account_sid,
          auth_token: cfg.twilio.auth_token,
          from_number: cfg.twilio.from_number,
          webhook_base_url: cfg.twilio.webhook_base_url,
        },
        signalwire: {
          space_url: cfg.signalwire?.space_url || "",
        },
        agents: {
          mode: cfg.agents.mode,
          mobile_numbers: cfg.agents.mobile_numbers,
          names: cfg.agents.names,
          timeout: cfg.agents.timeout,
          max_concurrent: cfg.agents.max_concurrent,
          enable_amd: cfg.agents.enable_amd === "true",
          extensions: cfg.agents.extensions,
        },
        dialer: {
          ring_timeout: cfg.dialer.ring_timeout,
          batch_delay: cfg.dialer.batch_delay,
          concurrent_calls: cfg.dialer.concurrent_calls,
        },
        system: {
          wsl_sudo_password: cfg.system?.wsl_sudo_password,
          ngrok_authtoken: cfg.system?.ngrok_authtoken,
        },
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (!cfg) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "#636e72" }}>
        <RefreshCw size={16} style={{ marginRight: 8 }} /> Loading config...
      </div>
    );
  }

  const usingSignalWire = !!(cfg.signalwire?.space_url?.trim());

  return (
    <div style={{ maxWidth: 700, display: "flex", flexDirection: "column", gap: 16 }}>

      <Section title="System">
        <Field label="WSL2 Sudo Password" value={cfg.system?.wsl_sudo_password || ""} onChange={(v) => update("system", "wsl_sudo_password", v)} type="password" placeholder="Your WSL2 user password" />
        <Field label="Ngrok Authtoken" value={cfg.system?.ngrok_authtoken || ""} onChange={(v) => update("system", "ngrok_authtoken", v)} type="password" placeholder="From dashboard.ngrok.com" />
      </Section>

      {/* Provider Selection */}
      <Section title="Call Provider">
        <div style={{ display: "flex", gap: 10, marginBottom: 10 }}>
          <ProviderCard
            name="Twilio"
            rate="$0.013/min"
            description="Default provider. Reliable, widely used."
            active={!usingSignalWire}
            onClick={() => update("signalwire", "space_url", "")}
          />
          <ProviderCard
            name="SignalWire"
            rate="$0.005/min"
            description="60% cheaper. Drop-in Twilio replacement."
            active={usingSignalWire}
            badge="RECOMMENDED"
            onClick={() => update("signalwire", "space_url", cfg.signalwire?.space_url || "yourspace.signalwire.com")}
          />
        </div>

        {usingSignalWire && (
          <div style={{ background: "rgba(0,184,148,0.06)", border: "1px solid rgba(0,184,148,0.2)", borderRadius: 6, padding: "12px 14px", display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ fontSize: 11, color: "#00b894", fontWeight: 700 }}>
              SignalWire Active — 60% cheaper than Twilio
            </div>
            <Field
              label="Space URL (e.g. yourspace.signalwire.com)"
              value={cfg.signalwire?.space_url || ""}
              onChange={(v) => update("signalwire", "space_url", v)}
              placeholder="yourspace.signalwire.com"
            />
            <div style={{ fontSize: 10, color: "#636e72" }}>
              Put your SignalWire <strong>Project ID</strong> in Account SID below,
              <strong> API Token</strong> in Auth Token, and <strong>SignalWire phone number</strong> in From Number.
            </div>
          </div>
        )}
      </Section>

      <Section title={usingSignalWire ? "SignalWire Credentials" : "Twilio Credentials"}>
        <Field label={usingSignalWire ? "Project ID (Account SID)" : "Account SID"} value={cfg.twilio.account_sid} onChange={(v) => update("twilio", "account_sid", v)} />
        <Field label={usingSignalWire ? "API Token (Auth Token)" : "Auth Token"} value={cfg.twilio.auth_token} onChange={(v) => update("twilio", "auth_token", v)} type="password" />
        <Field label="From Number (your phone number)" value={cfg.twilio.from_number} onChange={(v) => update("twilio", "from_number", v)} placeholder="+17868339866" />
        <Field label="Webhook URL (ngrok URL)" value={cfg.twilio.webhook_base_url} onChange={(v) => update("twilio", "webhook_base_url", v)} placeholder="https://xxx.ngrok-free.dev" />
      </Section>

      <Section title="Agent Mode">
        <div style={{ marginBottom: 10 }}>
          <label style={labelStyle}>Mode</label>
          <select className="vici-select" value={cfg.agents.mode} onChange={(e) => update("agents", "mode", e.target.value)}>
            <option value="voicemail_blast">Voicemail Blast — drop voicemail to everyone</option>
            <option value="mobile">Mobile Bridge — connect live to agent cellphone</option>
            <option value="softphone">Softphone — connect via SIP extension</option>
          </select>
          <div style={{ fontSize: 10, color: "#636e72", marginTop: 6 }}>
            {cfg.agents.mode === "voicemail_blast" && "Dials leads simultaneously, plays voicemail.mp3. Leads call back on your number."}
            {cfg.agents.mode === "mobile" && "When lead answers, system calls agent mobile. Both parties bridged together."}
            {cfg.agents.mode === "softphone" && "When lead answers, system connects to SIP extension via Asterisk."}
          </div>
        </div>

        {cfg.agents.mode === "voicemail_blast" ? (
          <>
            <Field label="Agent Mobile Numbers for callbacks (comma-separated E.164)" value={cfg.agents.mobile_numbers} onChange={(v) => update("agents", "mobile_numbers", v)} placeholder="+14145551234,+14145555678" />
            <Field label="Agent Names (comma-separated)" value={cfg.agents.names} onChange={(v) => update("agents", "names", v)} placeholder="Agent 1,Agent 2" />
          </>
        ) : cfg.agents.mode === "mobile" ? (
          <>
            <Field label="Mobile Numbers (comma-separated E.164)" value={cfg.agents.mobile_numbers} onChange={(v) => update("agents", "mobile_numbers", v)} placeholder="+14145551234,+14145555678" />
            <Field label="Agent Names (comma-separated)" value={cfg.agents.names} onChange={(v) => update("agents", "names", v)} placeholder="Agent 1,Agent 2" />
          </>
        ) : (
          <>
            <Field label="SIP Extensions (comma-separated)" value={cfg.agents.extensions} onChange={(v) => update("agents", "extensions", v)} placeholder="101,102" />
            <Field label="Agent Names (comma-separated)" value={cfg.agents.names} onChange={(v) => update("agents", "names", v)} placeholder="Agent 1,Agent 2" />
          </>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <Field label="Agent Timeout (s)" value={cfg.agents.timeout} onChange={(v) => update("agents", "timeout", v)} />
          <Field label="Max Concurrent" value={cfg.agents.max_concurrent} onChange={(v) => update("agents", "max_concurrent", v)} />
          <div>
            <label style={labelStyle}>AMD Enabled</label>
            <select className="vici-select" value={cfg.agents.enable_amd} onChange={(e) => update("agents", "enable_amd", e.target.value)}>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
        </div>
      </Section>

      <Section title="Voicemail">
        <VoicemailUploader />
      </Section>

      <Section title="Dialer Speed">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <Field label="Ring Timeout (s)" value={cfg.dialer.ring_timeout} onChange={(v) => update("dialer", "ring_timeout", v)} />
          <Field label="Batch Delay (s)" value={cfg.dialer.batch_delay} onChange={(v) => update("dialer", "batch_delay", v)} />
          <Field label="Concurrent Calls" value={cfg.dialer.concurrent_calls || "5"} onChange={(v) => update("dialer", "concurrent_calls", v)} />
        </div>
        <div style={{ fontSize: 10, color: "#636e72", marginTop: 4 }}>
          <strong style={{ color: "#fdcb6e" }}>Concurrent Calls</strong> — how many numbers to dial simultaneously.
          Paid accounts: 5–20 recommended. Trial accounts: max 1.
        </div>
      </Section>

      <div>
        <button className="vici-btn vici-btn-green" onClick={handleSave} disabled={saving} style={{ minWidth: 140 }}>
          <Save size={12} />
          {saving ? "Saving..." : saved ? "✓ Saved!" : "Save Settings"}
        </button>
      </div>
    </div>
  );
}

function ProviderCard({ name, rate, description, active, badge, onClick }: {
  name: string; rate: string; description: string;
  active: boolean; badge?: string; onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        flex: 1, padding: "12px 14px", borderRadius: 6, cursor: "pointer",
        border: `2px solid ${active ? "#00b894" : "#2d3436"}`,
        background: active ? "rgba(0,184,148,0.06)" : "#0d1b2a",
        transition: "all 0.15s",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <span style={{ fontWeight: 700, fontSize: 13, color: active ? "#00b894" : "#fff" }}>{name}</span>
        {badge && (
          <span style={{ fontSize: 9, fontWeight: 700, background: "#00b894", color: "#fff", padding: "2px 6px", borderRadius: 3 }}>
            {badge}
          </span>
        )}
      </div>
      <div style={{ fontSize: 16, fontWeight: 700, color: active ? "#00b894" : "#fdcb6e" }}>{rate}</div>
      <div style={{ fontSize: 10, color: "#636e72", marginTop: 2 }}>{description}</div>
      {active && <div style={{ fontSize: 10, color: "#00b894", marginTop: 4 }}>✓ Active</div>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="vici-card">
      <div style={{ fontSize: 10, fontWeight: 700, color: "#636e72", letterSpacing: 1, textTransform: "uppercase", marginBottom: 12, borderBottom: "1px solid #2d3436", paddingBottom: 8 }}>
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{children}</div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block", fontSize: 10, color: "#b2bec3",
  marginBottom: 4, textTransform: "uppercase", letterSpacing: 0.5,
};

function Field({ label, value, onChange, type = "text", placeholder }: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string;
}) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input className="vici-input" type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} />
    </div>
  );
}

function VoicemailUploader() {
  const [status, setStatus] = useState<"idle" | "uploading" | "ok" | "error">("idle");
  const [msg, setMsg] = useState("");
  const [vmUrl, setVmUrl] = useState("");

  const checkVoicemail = async () => {
    try {
      const r = await fetch("http://localhost:5000/ping");
      const d = await r.json();
      setVmUrl(d.voicemail_url || "");
      if (d.voicemail_exists) {
        setMsg(`Current: voicemail.mp3 (${(d.voicemail_size_bytes / 1024).toFixed(1)} KB)`);
        setStatus("ok");
      } else {
        setMsg("No voicemail.mp3 found — upload one below");
        setStatus("error");
      }
    } catch {
      setMsg("API not reachable");
      setStatus("error");
    }
  };

  const handleUpload = async (file: File) => {
    setStatus("uploading");
    setMsg("Uploading...");
    try {
      const r = await fetch("http://localhost:5000/api/voicemail/upload", {
        method: "POST",
        headers: { "Content-Type": file.type || "audio/mpeg" },
        body: file,
      });
      const d = await r.json();
      if (d.ok) {
        setStatus("ok");
        setMsg(`Uploaded (${(d.size_bytes / 1024).toFixed(1)} KB) — ready to use`);
      } else {
        setStatus("error");
        setMsg(d.error || "Upload failed");
      }
    } catch {
      setStatus("error");
      setMsg("Upload failed — API not reachable");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      {msg && (
        <div style={{
          fontSize: 11,
          color: status === "ok" ? "#00b894" : status === "error" ? "#d63031" : "#0984e3",
          background: status === "ok" ? "rgba(0,184,148,0.08)" : status === "error" ? "rgba(214,48,49,0.08)" : "rgba(9,132,227,0.08)",
          border: `1px solid ${status === "ok" ? "rgba(0,184,148,0.2)" : status === "error" ? "rgba(214,48,49,0.2)" : "rgba(9,132,227,0.2)"}`,
          borderRadius: 4, padding: "6px 10px",
        }}>{msg}</div>
      )}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button className="vici-btn vici-btn-blue" onClick={() => document.getElementById("vm-upload")?.click()} disabled={status === "uploading"}>
          {status === "uploading" ? "Uploading..." : "Upload voicemail.mp3"}
        </button>
        <button className="vici-btn vici-btn-ghost" onClick={checkVoicemail}>Check Status</button>
        {vmUrl && (
          <a href={vmUrl} target="_blank" rel="noreferrer" style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, color: "#0984e3", textDecoration: "none", padding: "6px 10px" }}>
            ▶ Test Audio
          </a>
        )}
      </div>
      <input id="vm-upload" type="file" accept=".mp3,.wav,audio/*" style={{ display: "none" }}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); e.target.value = ""; }} />
      <div style={{ fontSize: 10, color: "#636e72" }}>
        Upload your recorded message. Click "Test Audio" to verify it plays correctly before running a campaign.
      </div>
    </div>
  );
}
