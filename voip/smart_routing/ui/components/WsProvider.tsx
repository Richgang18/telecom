"use client";
import { useEffect, useRef } from "react";
import { useDialerStore } from "@/lib/store";
import { createWebSocket } from "@/lib/api";

const BASE = "http://localhost:5000";
let idCounter = 0;
const uid = () => String(++idCounter);

export default function WsProvider({ children }: { children: React.ReactNode }) {
  const {
    setWsConnected, setAgents, updateAgent, addLog,
    incStat, setSystem, setStats, resetStats,
    setActiveCampaignId, activeCampaignId,
  } = useDialerStore();
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeCampaignRef = useRef<string | null>(null);

  // Keep ref in sync with store value
  useEffect(() => {
    activeCampaignRef.current = activeCampaignId;
  }, [activeCampaignId]);

  // Poll active campaign every 3s to sync stats
  const startCampaignPoll = (campaignId: string) => {
    stopCampaignPoll();
    activeCampaignRef.current = campaignId;
    setActiveCampaignId(campaignId);

    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${BASE}/api/campaigns/${activeCampaignRef.current}`);
        if (!r.ok) return;
        const data = await r.json();
        setStats({
          totalCalls: data.dialed ?? 0,
          answered: data.answered ?? 0,
          voicemail: data.voicemail_dropped ?? 0,
          noAnswer: data.no_answer ?? 0,
          failed: data.failed ?? 0,
        });
      } catch {}
    }, 3000);
  };

  const stopCampaignPoll = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const connect = () => {
    const ws = createWebSocket(
      (data) => handleMessage(data),
      () => {
        setWsConnected(true);
        setSystem({ webhook: true });
      },
      () => {
        setWsConnected(false);
        setSystem({ webhook: false });
        retryRef.current = setTimeout(connect, 3000);
      }
    );
    wsRef.current = ws;
  };

  const handleMessage = (data: any) => {
    addLog({ id: uid(), ...data });

    switch (data.event) {
      case "init": {
        const agentList = Object.entries(data.agents || {}).map(([id, info]: any) => ({
          id,
          name: info.name,
          status: info.status,
          mobile: info.mobile,
          call_sid: info.call_sid,
        }));
        setAgents(agentList);
        break;
      }
      case "call_connected": {
        const agentId = String(data.agent);
        updateAgent(agentId, { status: "busy", call_sid: data.call_sid });
        // Don't incStat here — campaign poll handles counts
        break;
      }
      case "voicemail_dropped": {
        // Don't incStat here — campaign poll handles counts
        break;
      }
      case "inbound_callback": {
        addLog({ id: uid(), ...data });
        break;
      }
      case "agent_available": {
        const agentId = String(data.agent);
        updateAgent(agentId, { status: "available", call_sid: null });
        break;
      }
      case "no_answer": {
        // Don't incStat here — campaign poll handles counts
        break;
      }
      case "amd_machine": {
        // Don't incStat here — campaign poll handles counts
        break;
      }
      case "dialer_started": {
        setSystem({ dialer_running: true });
        resetStats();
        // Fetch the latest campaign id and start polling
        fetch(`${BASE}/api/campaigns`)
          .then((r) => r.json())
          .then((d) => {
            const campaigns = d.campaigns ?? [];
            const running = campaigns.find((c: any) => c.status === "running");
            if (running) startCampaignPoll(running.id);
          })
          .catch(() => {});
        break;
      }
      case "dialer_stopped": {
        setSystem({ dialer_running: false });
        // Do one final poll then stop
        if (activeCampaignRef.current) {
          fetch(`${BASE}/api/campaigns/${activeCampaignRef.current}`)
            .then((r) => r.json())
            .then((data) => {
              setStats({
                totalCalls: data.dialed ?? 0,
                answered: data.answered ?? 0,
                voicemail: data.voicemail_dropped ?? 0,
                noAnswer: data.no_answer ?? 0,
                failed: data.failed ?? 0,
              });
            })
            .catch(() => {});
        }
        stopCampaignPoll();
        setActiveCampaignId(null);
        break;
      }
    }
  };

  useEffect(() => {
    connect();

    // On mount, check if a campaign is already running (page reload mid-campaign)
    fetch(`${BASE}/api/campaigns`)
      .then((r) => r.json())
      .then((d) => {
        const campaigns = d.campaigns ?? [];
        const running = campaigns.find((c: any) => c.status === "running");
        if (running) {
          setSystem({ dialer_running: true });
          startCampaignPoll(running.id);
        }
      })
      .catch(() => {});

    return () => {
      wsRef.current?.close();
      if (retryRef.current) clearTimeout(retryRef.current);
      stopCampaignPoll();
    };
  }, []);

  return <>{children}</>;
}
