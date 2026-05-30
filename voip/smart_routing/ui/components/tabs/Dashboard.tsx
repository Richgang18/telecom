"use client";
import StatCard from "@/components/StatCard";
import AgentPanel from "@/components/AgentPanel";
import CampaignControls from "@/components/CampaignControls";
import CallChart from "@/components/CallChart";
import LiveLog from "@/components/LiveLog";
import { useDialerStore } from "@/lib/store";

export default function Dashboard() {
  const { totalCalls, answered, voicemail, noAnswer, failed, totalContacts, system } = useDialerStore();

  const answerRate = totalCalls > 0 ? Math.round((answered / totalCalls) * 100) : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, height: "100%", minHeight: 0 }}>
      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10 }}>
        <StatCard label="Total Contacts" value={totalContacts.toLocaleString()} color="#0984e3" />
        <StatCard label="Calls Made"     value={totalCalls}   color="#6c5ce7" />
        <StatCard label="Answered"       value={answered}     color="#00b894" sub={`${answerRate}% rate`} />
        <StatCard label="Voicemail"      value={voicemail}    color="#fdcb6e" />
        <StatCard label="No Answer"      value={noAnswer}     color="#d63031" />
        <StatCard label="Failed"         value={failed}       color="#636e72" />
      </div>

      {/* Middle row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 220px 220px", gap: 10 }}>
        <CampaignControls />
        <AgentPanel />
        <CallChart />
      </div>

      {/* Log */}
      <div style={{ flex: 1, minHeight: 0 }}>
        <LiveLog />
      </div>
    </div>
  );
}
