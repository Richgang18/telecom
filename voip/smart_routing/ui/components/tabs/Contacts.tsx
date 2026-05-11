"use client";
import { useDialerStore } from "@/lib/store";
import { useState, useCallback } from "react";
import { Upload, Trash2 } from "lucide-react";

interface Contact { name: string; phone: string; }

export default function Contacts() {
  const { setTotalContacts } = useDialerStore();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [dragging, setDragging] = useState(false);

  const parseCSV = (text: string) => {
    const lines = text.trim().split("\n");
    const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
    const phoneIdx = headers.findIndex((h) => h.includes("phone"));
    const firstIdx = headers.findIndex((h) => h.includes("first"));
    const lastIdx  = headers.findIndex((h) => h.includes("last"));
    const nameIdx  = headers.findIndex((h) => h === "name");

    const parsed: Contact[] = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
      const phone = cols[phoneIdx] || "";
      if (!phone) continue;
      let name = "";
      if (nameIdx >= 0) name = cols[nameIdx];
      else if (firstIdx >= 0) name = `${cols[firstIdx] || ""} ${cols[lastIdx] || ""}`.trim();
      parsed.push({ name: name || "Unknown", phone });
    }
    return parsed;
  };

  const loadFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const parsed = parseCSV(text);
      setContacts(parsed);
      setTotalContacts(parsed.length);
    };
    reader.readAsText(file);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) loadFile(file);
  }, []);

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
          onChange={(e) => { const f = e.target.files?.[0]; if (f) loadFile(f); }}
        />
      </div>

      {/* Stats bar */}
      {contacts.length > 0 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(0,184,148,0.08)",
            border: "1px solid rgba(0,184,148,0.2)",
            borderRadius: 4,
            padding: "8px 12px",
          }}
        >
          <span style={{ color: "#00b894", fontSize: 12, fontWeight: 600 }}>
            ✓ {contacts.length.toLocaleString()} contacts loaded
          </span>
          <button
            className="vici-btn vici-btn-ghost"
            onClick={() => { setContacts([]); setTotalContacts(0); }}
            style={{ fontSize: 11 }}
          >
            <Trash2 size={11} /> Clear
          </button>
        </div>
      )}

      {/* Table */}
      {contacts.length > 0 && (
        <div className="vici-card" style={{ flex: 1, minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: "#636e72", letterSpacing: 1, textTransform: "uppercase", marginBottom: 8 }}>
            Contact List (showing first 200)
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
  padding: "6px 10px",
  textAlign: "left",
  color: "#636e72",
  fontWeight: 700,
  fontSize: 10,
  textTransform: "uppercase",
  letterSpacing: 0.5,
};

const td: React.CSSProperties = {
  padding: "5px 10px",
  color: "#dfe6e9",
};
