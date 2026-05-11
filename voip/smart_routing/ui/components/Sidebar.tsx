"use client";
import { useDialerStore } from "@/lib/store";
import {
  LayoutDashboard,
  Phone,
  Users,
  BarChart2,
  Settings,
  FileText,
} from "lucide-react";

const TABS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "campaign",  label: "Campaign",  icon: Phone },
  { id: "agents",    label: "Agents",    icon: Users },
  { id: "reports",   label: "Reports",   icon: BarChart2 },
  { id: "contacts",  label: "Contacts",  icon: FileText },
  { id: "settings",  label: "Settings",  icon: Settings },
];

export default function Sidebar() {
  const { activeTab, setActiveTab } = useDialerStore();

  return (
    <aside
      style={{
        width: 180,
        background: "#16213e",
        borderRight: "1px solid #2d3436",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}
    >
      {/* Section label */}
      <div
        style={{
          padding: "12px 16px 6px",
          fontSize: 9,
          fontWeight: 700,
          color: "#636e72",
          letterSpacing: 1.5,
          textTransform: "uppercase",
        }}
      >
        Navigation
      </div>

      {TABS.map(({ id, label, icon: Icon }) => {
        const active = activeTab === id;
        return (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 16px",
              background: active ? "#0f3460" : "transparent",
              borderLeft: active ? "3px solid #e94560" : "3px solid transparent",
              color: active ? "#fff" : "#b2bec3",
              fontSize: 12,
              fontWeight: active ? 600 : 400,
              cursor: "pointer",
              border: "none",
              width: "100%",
              textAlign: "left",
              transition: "all 0.1s",
            }}
          >
            <Icon size={14} />
            {label}
          </button>
        );
      })}
    </aside>
  );
}
