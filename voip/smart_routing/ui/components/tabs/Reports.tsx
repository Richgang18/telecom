"use client";
import { useDialerStore } from "@/lib/store";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Download } from "lucide-react";

export default function Reports() {
  const { answered, voicemail, noAnswer, totalCalls, callLog } = useDialerStore();

  const chartData = [
    { name: "Answered",  value: answered,  fill: "#00b894" },
    { name: "Voicemail", value: voicemail,  fill: "#fdcb6e" },
    { name: "No Answer", value: noAnswer,   fill: "#d63031" },
    { name: "Total",     value: totalCalls, fill: "#0984e3" },
  ];

  const answerRate = totalCalls > 0 ? ((answered / totalCalls) * 100).toFixed(1) : "0.0";
  const vmRate     = totalCalls > 0 ? ((voicemail / totalCalls) * 100).toFixed(1) : "0.0";

  const exportCSV = () => {
    const rows = [["Timestamp", "Event", "Details"]];
    callLog.forEach((e) => {
      rows.push([e.ts, e.event, e.msg || JSON.stringify(e)]);
    });
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `call_report_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
        {[
          { label: "Total Calls",   value: totalCalls, color: "#0984e3" },
          { label: "Answer Rate",   value: `${answerRate}%`, color: "#00b894" },
          { label: "Voicemail Rate",value: `${vmRate}%`, color: "#fdcb6e" },
          { label: "Answered",      value: answered, color: "#00b894" },
        ].map((k) => (
          <div key={k.label} className="vici-card" style={{ borderTop: `3px solid ${k.color}` }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: k.color }}>{k.value}</div>
            <div style={{ fontSize: 10, color: "#b2bec3", textTransform: "uppercase", letterSpacing: 0.5, marginTop: 4 }}>{k.label}</div>
          </div>
        ))}
      </div>

      {/* Bar chart */}
      <div className="vici-card">
        <div style={{ fontSize: 10, fontWeight: 700, color: "#636e72", letterSpacing: 1, textTransform: "uppercase", marginBottom: 12 }}>
          Call Results Overview
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} barSize={40}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3436" />
            <XAxis dataKey="name" tick={{ fill: "#b2bec3", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#b2bec3", fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: "#16213e", border: "1px solid #2d3436", fontSize: 11 }}
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} fill="#0984e3" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Export */}
      <div>
        <button className="vici-btn vici-btn-blue" onClick={exportCSV}>
          <Download size={12} />
          Export Call Log CSV
        </button>
      </div>
    </div>
  );
}
