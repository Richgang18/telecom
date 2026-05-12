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

  return (
    <div style={{ maxWidth: 700, display: "flex", flexDirection: "column", gap: 16 }}>
      <Section title="System">
        <Field
          label="WSL2 Sudo Password (used to start Asterisk silently)"
          value={cfg.system?.wsl_sudo_password || ""}
          onChange={(v) => update("system", "wsl_sudo_password", v)}
          type="password"
          placeholder="Your WSL2 user password"
        />
        <Field
          label="Ngrok Authtoken (from dashboard.ngrok.com)"
          value={cfg.system?.ngrok_authtoken || ""}
          onChange={(v) => update("system", "ngrok_authtoken", v)}
          type="password"
          placeholder="Paste your ngrok authtoken here"
        />
        <div style={{ fontSize: 10, color: "#636e72", marginTop: -6 }}>
          Get your authtoken at: https://dashboard.ngrok.com/get-started/your-authtoken
        </div>
      </Section>

      <Section title="Twilio">
        <Field label="Account SID"   value={cfg.twilio.account_sid}    onChange={(v) => update("twilio", "account_sid", v)} />
        <Field label="Auth Token"    value={cfg.twilio.auth_token}     onChange={(v) => update("twilio", "auth_token", v)} type="password" />
        <Field label="From Number"   value={cfg.twilio.from_number}    onChange={(v) => update("twilio", "from_number", v)} placeholder="+17868339866" />
        <Field label="Webhook URL"   value={cfg.twilio.webhook_base_url} onChange={(v) => update("twilio", "webhook_base_url", v)} placeholder="https://xxx.ngrok-free.dev" />
      </Section>

      <Section title="Agent Mode">
        <div style={{ marginBottom: 10 }}>
          <label style={labelStyle}>Mode</label>
          <select
            className="vici-select"
            value={cfg.agents.mode}
            onChange={(e) => update("agents", "mode", e.target.value)}
          >
            <option value="mobile">Mobile (calls your cellphone)</option>
            <option value="softphone">Softphone (SIP extension)</option>
          </select>
        </div>

        {cfg.agents.mode === "mobile" ? (
          <>
            <Field label="Mobile Numbers (comma-separated E.164)" value={cfg.agents.mobile_numbers} onChange={(v) => update("agents", "mobile_numbers", v)} placeholder="+14145551234,+14145555678" />
            <Field label="Agent Names (comma-separated)"          value={cfg.agents.names}          onChange={(v) => update("agents", "names", v)} placeholder="Agent 1,Agent 2" />
          </>
        ) : (
          <>
            <Field label="SIP Extensions (comma-separated)" value={cfg.agents.extensions}    onChange={(v) => update("agents", "extensions", v)} placeholder="101,102" />
            <Field label="Agent Names (comma-separated)"    value={cfg.agents.names}          onChange={(v) => update("agents", "names", v)} placeholder="Agent 1,Agent 2" />
          </>
        )}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <Field label="Agent Timeout (s)"   value={cfg.agents.timeout}        onChange={(v) => update("agents", "timeout", v)} />
          <Field label="Max Concurrent"      value={cfg.agents.max_concurrent} onChange={(v) => update("agents", "max_concurrent", v)} />
          <div>
            <label style={labelStyle}>AMD Enabled</label>
            <select
              className="vici-select"
              value={cfg.agents.enable_amd}
              onChange={(e) => update("agents", "enable_amd", e.target.value)}
            >
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </div>
        </div>
      </Section>

      <Section title="Dialer">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Field label="Ring Timeout (s)" value={cfg.dialer.ring_timeout} onChange={(v) => update("dialer", "ring_timeout", v)} />
          <Field label="Batch Delay (s)"  value={cfg.dialer.batch_delay}  onChange={(v) => update("dialer", "batch_delay", v)} />
        </div>
      </Section>

      <div>
        <button
          className="vici-btn vici-btn-green"
          onClick={handleSave}
          disabled={saving}
          style={{ minWidth: 140 }}
        >
          <Save size={12} />
          {saving ? "Saving..." : saved ? "✓ Saved!" : "Save Settings"}
        </button>
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
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
          borderBottom: "1px solid #2d3436",
          paddingBottom: 8,
        }}
      >
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{children}</div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block",
  fontSize: 10,
  color: "#b2bec3",
  marginBottom: 4,
  textTransform: "uppercase",
  letterSpacing: 0.5,
};

function Field({
  label, value, onChange, type = "text", placeholder,
}: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string;
}) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input
        className="vici-input"
        type={type}
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}
