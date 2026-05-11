"use client";
import { useDialerStore } from "@/lib/store";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

const COLORS = ["#00b894", "#fdcb6e", "#d63031", "#636e72"];

export default function CallChart() {
  const { answered, voicemail, noAnswer, totalCalls } = useDialerStore();

  const data = [
    { name: "Answered",  value: answered },
    { name: "Voicemail", value: voicemail },
    { name: "No Answer", value: noAnswer },
    { name: "Other",     value: Math.max(0, totalCalls - answered - voicemail - noAnswer) },
  ].filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <div
        className="vici-card"
        style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 180 }}
      >
        <div style={{ color: "#636e72", fontSize: 12 }}>No call data yet</div>
      </div>
    );
  }

  return (
    <div className="vici-card">
      <div
        style={{
          fontSize: 10,
          fontWeight: 700,
          color: "#636e72",
          letterSpacing: 1,
          textTransform: "uppercase",
          marginBottom: 8,
        }}
      >
        Call Breakdown
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={45}
            outerRadius={70}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: "#16213e", border: "1px solid #2d3436", fontSize: 11 }}
            labelStyle={{ color: "#dfe6e9" }}
          />
          <Legend
            iconSize={8}
            wrapperStyle={{ fontSize: 10, color: "#b2bec3" }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
