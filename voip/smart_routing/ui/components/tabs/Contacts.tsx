"use client";
import { useDialerStore } from "@/lib/store";
import { useState, useCallback, useEffect } from "react";
import { Upload, Trash2, CheckCircle, AlertCircle, RefreshCw } from "lucide-react";

interface Contact { name: string; phone: string; }

export default function Contacts() {
  const { setTotalContacts } = useDialerStore();
  const [contacts, setContacts]     = useState<Contact[]>([]);
  const [dragging, setDragging]     = useState(false);
  const [saving, setSaving]         = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "ok" | "error">("idle");
  const [saveMsg, setSaveMsg]       = useState("");
  const [loading, setLoading]       = useState(true);

  // Load existing contacts from server on mount
  useEffect(() => {
    fetch("http://localhost:5000/api/contacts")
      .then((r) => r.json())
      .then((d) => {
        if (d.contacts?.length > 0) {
          setContacts(d.contacts);
          setTotalContacts(d.total);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [setTotalContacts]);

  const parseCSV = (text: string): Contact[] => {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) return [];

    const headers = lines[0].split(",").map((h) => h.trim().replace(/^"|"$/g, "").toLowerCase());
    const phoneIdx = headers.findIndex((h) => h.includes("phone"));
    const firstIdx = headers.findIndex((h) => h.includes("first"));
    const lastIdx  = headers.findIndex((h) => h.includes("last"));
    const nameIdx  = headers.findIndex((h) => h === "name");

    if (phoneIdx === -1) {
      setSaveStatus("error");
      setSaveMsg("CSV must have a 'Phone' column");
      return [];
    }

    const parsed: Contact[] = [];
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      const cols = line.split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
      const phone = cols[phoneIdx] || "";
      if (!phone) continue;
      let name = "";
      if (nameIdx >= 0) name = cols[nameIdx] || "";
      else if (firstIdx >= 0) name = `${cols[firstIdx] || ""} ${cols[lastIdx] || ""}`.trim();
      parsed.push({ name: name || "Unknown", phone });
    }
    return parsed;
  };

  const saveToServer = async (parsed: Contact[]) => {
    setSaving(true);
    setSaveStatus("idle");
    try {
      const r = await fetch("http://localhost:5000/api/contacts/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contacts: parsed }),
      });
      const d = await r.json();
      if (d.ok) {
        setSaveStatus("ok");
        setSaveMsg(`${d.total.toLocaleString()} contacts saved to server`);
        setTotalContacts(d.total);
      } else {
        setSaveStatus("error");
        setSaveMsg(d.error || "Failed to save");
      }
    } catch (e) {
      setSaveStatus("error");
      setSaveMsg("Could not reach API server");
    } finally {
      setSaving(false);
    }
  };

  const loadFile = (file: File) => {
    setSaveStatus("idle");
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const parsed = parseCSV(text);
      if (parsed.length > 0) {
        setContacts(parsed);
        saveToServer(parsed);
      }
    };
    reader.readAsText(file);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) loadFile(file);
  }, []);

  const handleClear = async () => {
    setContacts([]);
    setTotalContacts(0);
    setSaveStatus("idle");
    // Clear on server too
    await fetch("http://localhost:5000/api/contacts/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contacts: [] }),
    }).catch(() => {});
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, height: "100%", minHeight: 0 }}>

      {/* Upload zone */}
      <div
        className="vici-card"
        onDrop={onDrop}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        style={{
          border: `2px dashed ${dragging ? "#0984e3" : "#2d3436"}`,
          textAlign: "center",
          padding: "24px 16px",
          cursor: "pointer",
          transition: "border-color 0.15s",
        }}
        onClick={() => document.getElementById("csv-input")?.click()}
      >
        <Upload size={24} color={dragging ? "#0984e3" : "#636e72"} style={{ margin: "0 auto 8px" }} />
        <div style={{ fontSize: 13, color: "#b2bec3" }}>
          Drop CSV file here or <span style={{ color: "#0984e3" }}>click to browse</span>
        </div>
        <div style={{ fontSize: 10, color: "#636e72", marginTop: 4 }}>
          Required column: Phone | Optional: Firstname, Lastname
        </div>
        <input
          id="csv-input"
          type="file"
          accept=".csv"
          style={{ display: "none" }}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) loadFile(f); e.target.value = ""; }}
        />
      </div>

      {/* Save status */}
      {saving && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#0984e3" }}>
          <RefreshCw size={13} style={{ animation: "spin 1s linear infinite" }} />
          Saving contacts to server...
        </div>
      )}
      {saveStatus === "ok" && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#00b894",
          background: "rgba(0,184,148,0.08)", border: "1px solid rgba(0,184,148,0.2)", borderRadius: 4, padding: "8px 12px" }}>
          <CheckCircle size={14} />
          {saveMsg}
        </div>
      )}
      {saveStatus === "error" && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "#d63031",
          background: "rgba(214,48,49,0.08)", border: "1px solid rgba(214,48,49,0.2)", borderRadius: 4, padding: "8px 12px" }}>
          <AlertCircle size={14} />
          {saveMsg}
        </div>
      )}

      {/* Stats bar */}
      {contacts.length > 0 && (
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "rgba(0,184,148,0.08)", border: "1px solid rgba(0,184,148,0.2)",
          borderRadius: 4, padding: "8px 12px",
        }}>
          <span style={{ color: "#00b894", fontSize: 12, fontWeight: 600 }}>
            {contacts.length.toLocaleString()} contacts loaded
            {saveStatus === "ok" && " — saved to dialer"}
          </span>
          <button className="vici-btn vici-btn-ghost" onClick={handleClear} style={{ fontSize: 11 }}>
            <Trash2 size={11} /> Clear
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div style={{ color: "#636e72", fontSize: 12, textAlign: "center", padding: "20px 0" }}>
          Loading existing contacts...
        </div>
      )}

      {/* Table */}
      {contacts.length > 0 && (
        <div className="vici-card" style={{ flex: 1, minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#636e72", letterSpacing: 1,
            textTransform: "uppercase", marginBottom: 8, display: "flex", justifyContent: "space-between" }}>
            <span>Contact List</span>
            <span style={{ color: "#0984e3" }}>
              {contacts.length > 200 ? `Showing 200 of ${contacts.length.toLocaleString()}` : `${contacts.length} total`}
            </span>
          </div>
          <div style={{ overflowY: "auto", flex: 1 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr style={{ background: "#0d1b2a", position: "sticky", top: 0 }}>
                  <th style={th}>#</th>
                  <th style={th}>Name</th>
                  <th style={th}>Phone</th>
                </tr>
              </thead>
              <tbody>
                {contacts.slice(0, 200).map((c, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid #1a1a2e" }}>
                    <td style={td}>{i + 1}</td>
                    <td style={td}>{c.name}</td>
                    <td style={{ ...td, color: "#74b9ff", fontFamily: "monospace" }}>{c.phone}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = {
  padding: "6px 10px", textAlign: "left", color: "#636e72",
  fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5,
};
const td: React.CSSProperties = { padding: "5px 10px", color: "#dfe6e9" };
