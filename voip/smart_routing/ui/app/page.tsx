"use client";
import { useState, useCallback } from "react";
import TopBar from "@/components/TopBar";
import Sidebar from "@/components/Sidebar";
import WsProvider from "@/components/WsProvider";
import LoadingScreen from "@/components/LoadingScreen";
import Dashboard from "@/components/tabs/Dashboard";
import Settings from "@/components/tabs/Settings";
import Contacts from "@/components/tabs/Contacts";
import Reports from "@/components/tabs/Reports";
import Agents from "@/components/tabs/Agents";
import { useDialerStore } from "@/lib/store";

function TabContent() {
  const { activeTab } = useDialerStore();
  switch (activeTab) {
    case "dashboard": return <Dashboard />;
    case "campaign":  return <Dashboard />;
    case "settings":  return <Settings />;
    case "contacts":  return <Contacts />;
    case "reports":   return <Reports />;
    case "agents":    return <Agents />;
    default:          return <Dashboard />;
  }
}

function MainApp() {
  return (
    <WsProvider>
      <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
        <TopBar />
        <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
          <Sidebar />
          <main style={{ flex: 1, padding: 14, overflowY: "auto", background: "#1a1a2e" }}>
            <TabContent />
          </main>
        </div>
      </div>
    </WsProvider>
  );
}

export default function Home() {
  const [ready, setReady] = useState(false);
  const handleReady = useCallback(() => setReady(true), []);

  return (
    <>
      {!ready && <LoadingScreen onReady={handleReady} />}
      {/* Render main app in background so it's ready when loading screen fades */}
      <div style={{ visibility: ready ? "visible" : "hidden", height: "100vh" }}>
        <MainApp />
      </div>
    </>
  );
}
