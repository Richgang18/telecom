"use client";

interface Props {
  label: string;
  value: number | string;
  color?: string;
  sub?: string;
}

export default function StatCard({ label, value, color = "#0984e3", sub }: Props) {
  return (
    <div
      className="vici-card"
      style={{ borderTop: `3px solid ${color}`, minWidth: 120 }}
    >
      <div style={{ fontSize: 26, fontWeight: 700, color, lineHeight: 1 }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: "#b2bec3", marginTop: 4, textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label}
      </div>
      {sub && (
        <div style={{ fontSize: 10, color: "#636e72", marginTop: 2 }}>{sub}</div>
      )}
    </div>
  );
}
