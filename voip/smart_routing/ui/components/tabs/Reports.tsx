"use client";
import { useDialerStore } from "@/lib/store";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Download, ChevronLeft, RefreshCw } from "lucide-react";
import { useEffect, useState, useCallback } from "react";
import * as XLSX from "xlsx";

const BASE = "http://localhost:5000";

// ── Types ────────────────────────────────────────────────────────────────────

interface CampaignSummary {
  id: string;
  started_at: string;
  ended_at: string | null;
  status: "running" | "completed";
  total_contacts: number;
  dialed: number;
  answered: number;
  voicemail_dropped: number;
  no_answer: number;
  failed: number;
}

interface CallRecord {
  call_sid: string;
  name: string;
  phone: string;
  status: string;
  answered_by: string;
  timestamp: string;
  duration: number;
}

interface CampaignDetail extends CampaignSummary {
  calls: CallRecord[];
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function statusBadge(status: string) {
  const colors: Record<string, string> = {
    running: "#fdcb6e",
    completed: "#00b894",
    answered: "#00b894",
    voicemail_dropped: "#fdcb6e",
    no_answer: "#d63031",
    failed: "#e94560",
  };
  const color = colors[status] ?? "#b2bec3";
  return (
    <span
      style={{
        background: `${color}22`,
        color,
        border: `1px solid ${color}55`,
        borderRadius: 4,
        padding: "2px 8px",
        fontSize: 11,
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: 0.5,
      }}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}

// ── Campaign List ─────────────────────────────────────────────────────────────

function CampaignList({
  campaigns,
  loading,
  onSelect,
  onRefresh,
}: {
  campaigns: CampaignSummary[];
  loading: boolean;
  onSelect: (id: string) => void;
  onRefresh: () => void;
}) {
  if (loading) {
    return (
      <div style={{ color: "#b2bec3", textAlign: "center", padding: 32, fontSize: 13 }}>
        Loading campaigns…
      </div>
    );
  }

  if (campaigns.length === 0) {
    return (
      <div style={{ color: "#636e72", textAlign: "center", padding: 32, fontSize: 13 }}>
        No campaigns yet. Start the dialer to create one.
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {campaigns.map((c) => {
        const answerRate =
          c.dialed > 0 ? ((c.answered / c.dialed) * 100).toFixed(1) : "0.0";
        return (
          <div
            key={c.id}
            onClick={() => onSelect(c.id)}
            style={{
              background: "#16213e",
              border: "1px solid #2d3436",
              borderRadius: 8,
              padding: "12px 16px",
              cursor: "pointer",
              transition: "border-color 0.15s",
            }}
            onMouseEnter={(e) =>
              ((e.currentTarget as HTMLDivElement).style.borderColor = "#e94560")
            }
            onMouseLeave={(e) =>
              ((e.currentTarget as HTMLDivElement).style.borderColor = "#2d3436")
            }
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <span style={{ fontWeight: 700, fontSize: 13, color: "#dfe6e9" }}>
                {c.id}
              </span>
              {statusBadge(c.status)}
            </div>
            <div style={{ fontSize: 11, color: "#636e72", marginBottom: 8 }}>
              {fmtDate(c.started_at)}
              {c.ended_at ? ` → ${fmtDate(c.ended_at)}` : " (running)"}
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(5, 1fr)",
                gap: 8,
              }}
            >
              {[
                { label: "Dialed", value: c.dialed, color: "#0984e3" },
                { label: "Answered", value: c.answered, color: "#00b894" },
                { label: "Voicemail", value: c.voicemail_dropped, color: "#fdcb6e" },
                { label: "No Answer", value: c.no_answer, color: "#d63031" },
                { label: "Ans Rate", value: `${answerRate}%`, color: "#a29bfe" },
              ].map((s) => (
                <div key={s.label} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: s.color }}>
                    {s.value}
                  </div>
                  <div
                    style={{
                      fontSize: 9,
                      color: "#636e72",
                      textTransform: "uppercase",
                      letterSpacing: 0.5,
                    }}
                  >
                    {s.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Campaign Detail ───────────────────────────────────────────────────────────

function CampaignDetailView({
  campaign,
  onBack,
}: {
  campaign: CampaignDetail;
  onBack: () => void;
}) {
  const exportXLSX = () => {
    const rows = campaign.calls.map((c) => ({
      Name: c.name,
      Phone: c.phone,
      Status: c.status,
      "Answered By": c.answered_by,
      Timestamp: c.timestamp,
      "Duration (s)": c.duration,
    }));
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Calls");
    XLSX.writeFile(wb, `${campaign.id}.xlsx`);
  };

  const exportCSV = async () => {
    const res = await fetch(`${BASE}/api/campaigns/${campaign.id}/export`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${campaign.id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const answerRate =
    campaign.dialed > 0
      ? ((campaign.answered / campaign.dialed) * 100).toFixed(1)
      : "0.0";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button
          onClick={onBack}
          style={{
            background: "none",
            border: "1px solid #2d3436",
            borderRadius: 6,
            color: "#b2bec3",
            cursor: "pointer",
            padding: "4px 10px",
            display: "flex",
            alignItems: "center",
            gap: 4,
            fontSize: 12,
          }}
        >
          <ChevronLeft size={14} /> Back
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: "#dfe6e9" }}>
            {campaign.id}
          </div>
          <div style={{ fontSize: 11, color: "#636e72" }}>
            {fmtDate(campaign.started_at)}
            {campaign.ended_at ? ` → ${fmtDate(campaign.ended_at)}` : " (running)"}
          </div>
        </div>
        {statusBadge(campaign.status)}
      </div>

      {/* KPI row */}
      <div
        style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}
      >
        {[
          { label: "Dialed", value: campaign.dialed, color: "#0984e3" },
          { label: "Answered", value: campaign.answered, color: "#00b894" },
          { label: "Voicemail", value: campaign.voicemail_dropped, color: "#fdcb6e" },
          { label: "No Answer", value: campaign.no_answer, color: "#d63031" },
          { label: "Ans Rate", value: `${answerRate}%`, color: "#a29bfe" },
        ].map((k) => (
          <div
            key={k.label}
            className="vici-card"
            style={{ borderTop: `3px solid ${k.color}`, textAlign: "center" }}
          >
            <div style={{ fontSize: 24, fontWeight: 700, color: k.color }}>
              {k.value}
            </div>
            <div
              style={{
                fontSize: 9,
                color: "#b2bec3",
                textTransform: "uppercase",
                letterSpacing: 0.5,
                marginTop: 4,
              }}
            >
              {k.label}
            </div>
          </div>
        ))}
      </div>

      {/* Export buttons */}
      <div style={{ display: "flex", gap: 8 }}>
        <button className="vici-btn vici-btn-blue" onClick={exportXLSX}>
          <Download size={12} />
          Export Excel (.xlsx)
        </button>
        <button className="vici-btn" onClick={exportCSV}
          style={{ background: "#2d3436", color: "#b2bec3", border: "1px solid #636e72" }}>
          <Download size={12} />
          Export CSV
        </button>
      </div>

      {/* Call log table */}
      <div className="vici-card" style={{ padding: 0, overflow: "hidden" }}>
        <div
          style={{
            padding: "10px 14px",
            fontSize: 10,
            fontWeight: 700,
            color: "#636e72",
            letterSpacing: 1,
            textTransform: "uppercase",
            borderBottom: "1px solid #2d3436",
          }}
        >
          Call Log ({campaign.calls.length} calls)
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#0f1923" }}>
                {["Name", "Phone", "Status", "Answered By", "Timestamp", "Duration"].map(
                  (h) => (
                    <th
                      key={h}
                      style={{
                        padding: "8px 12px",
                        textAlign: "left",
                        color: "#636e72",
                        fontWeight: 600,
                        fontSize: 10,
                        textTransform: "uppercase",
                        letterSpacing: 0.5,
                        borderBottom: "1px solid #2d3436",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {campaign.calls.length === 0 ? (
                <tr>
                  <td
                    colSpan={6}
                    style={{
                      padding: 24,
                      textAlign: "center",
                      color: "#636e72",
                      fontSize: 12,
                    }}
                  >
                    No calls recorded yet.
                  </td>
                </tr>
              ) : (
                campaign.calls.map((call, i) => (
                  <tr
                    key={call.call_sid || i}
                    style={{
                      borderBottom: "1px solid #1a2a3a",
                      background: i % 2 === 0 ? "transparent" : "#0f1923",
                    }}
                  >
                    <td style={{ padding: "7px 12px", color: "#dfe6e9" }}>
                      {call.name || "—"}
                    </td>
                    <td style={{ padding: "7px 12px", color: "#b2bec3", fontFamily: "monospace" }}>
                      {call.phone}
                    </td>
                    <td style={{ padding: "7px 12px" }}>{statusBadge(call.status)}</td>
                    <td style={{ padding: "7px 12px", color: "#636e72", fontSize: 11 }}>
                      {call.answered_by || "—"}
                    </td>
                    <td style={{ padding: "7px 12px", color: "#636e72", fontSize: 11, whiteSpace: "nowrap" }}>
                      {fmtDate(call.timestamp)}
                    </td>
                    <td style={{ padding: "7px 12px", color: "#b2bec3" }}>
                      {call.duration ? `${call.duration}s` : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Main Reports Tab ──────────────────────────────────────────────────────────

export default function Reports() {
  const { answered, voicemail, noAnswer, totalCalls, callLog } = useDialerStore();

  // Campaign history state
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(false);
  const [selectedCampaign, setSelectedCampaign] = useState<CampaignDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchCampaigns = useCallback(async () => {
    setCampaignsLoading(true);
    try {
      const res = await fetch(`${BASE}/api/campaigns`);
      const data = await res.json();
      setCampaigns(data.campaigns ?? []);
    } catch {
      // API not reachable yet
    } finally {
      setCampaignsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCampaigns();
  }, [fetchCampaigns]);

  const handleSelectCampaign = async (id: string) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`${BASE}/api/campaigns/${id}`);
      const data = await res.json();
      setSelectedCampaign(data);
    } catch {
      // ignore
    } finally {
      setDetailLoading(false);
    }
  };

  const chartData = [
    { name: "Answered", value: answered, fill: "#00b894" },
    { name: "Voicemail", value: voicemail, fill: "#fdcb6e" },
    { name: "No Answer", value: noAnswer, fill: "#d63031" },
    { name: "Total", value: totalCalls, fill: "#0984e3" },
  ];

  const answerRate =
    totalCalls > 0 ? ((answered / totalCalls) * 100).toFixed(1) : "0.0";
  const vmRate =
    totalCalls > 0 ? ((voicemail / totalCalls) * 100).toFixed(1) : "0.0";

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
      {/* ── Live session stats ── */}
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          color: "#636e72",
          letterSpacing: 1,
          textTransform: "uppercase",
        }}
      >
        Current Session
      </div>

      {/* KPI row */}
      <div
        style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}
      >
        {[
          { label: "Total Calls", value: totalCalls, color: "#0984e3" },
          { label: "Answer Rate", value: `${answerRate}%`, color: "#00b894" },
          { label: "Voicemail Rate", value: `${vmRate}%`, color: "#fdcb6e" },
          { label: "Answered", value: answered, color: "#00b894" },
        ].map((k) => (
          <div
            key={k.label}
            className="vici-card"
            style={{ borderTop: `3px solid ${k.color}` }}
          >
            <div style={{ fontSize: 28, fontWeight: 700, color: k.color }}>
              {k.value}
            </div>
            <div
              style={{
                fontSize: 10,
                color: "#b2bec3",
                textTransform: "uppercase",
                letterSpacing: 0.5,
                marginTop: 4,
              }}
            >
              {k.label}
            </div>
          </div>
        ))}
      </div>

      {/* Bar chart */}
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
          Call Results Overview
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} barSize={40}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2d3436" />
            <XAxis
              dataKey="name"
              tick={{ fill: "#b2bec3", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: "#b2bec3", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#16213e",
                border: "1px solid #2d3436",
                fontSize: 11,
              }}
              cursor={{ fill: "rgba(255,255,255,0.04)" }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]} fill="#0984e3" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Export live log */}
      <div>
        <button className="vici-btn vici-btn-blue" onClick={exportCSV}>
          <Download size={12} />
          Export Call Log CSV
        </button>
      </div>

      {/* ── Campaign History ── */}
      <div
        style={{
          borderTop: "1px solid #2d3436",
          paddingTop: 16,
          marginTop: 4,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 12,
          }}
        >
          <div
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: "#636e72",
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            Campaign History
          </div>
          {!selectedCampaign && (
            <button
              onClick={fetchCampaigns}
              style={{
                background: "none",
                border: "1px solid #2d3436",
                borderRadius: 6,
                color: "#636e72",
                cursor: "pointer",
                padding: "3px 8px",
                display: "flex",
                alignItems: "center",
                gap: 4,
                fontSize: 11,
              }}
            >
              <RefreshCw size={11} /> Refresh
            </button>
          )}
        </div>

        {detailLoading ? (
          <div
            style={{ color: "#b2bec3", textAlign: "center", padding: 32, fontSize: 13 }}
          >
            Loading campaign…
          </div>
        ) : selectedCampaign ? (
          <CampaignDetailView
            campaign={selectedCampaign}
            onBack={() => setSelectedCampaign(null)}
          />
        ) : (
          <CampaignList
            campaigns={campaigns}
            loading={campaignsLoading}
            onSelect={handleSelectCampaign}
            onRefresh={fetchCampaigns}
          />
        )}
      </div>
    </div>
  );
}
