"use client";
import { useEffect, useRef } from "react";
import { useDialerStore } from "@/lib/store";
import { createWebSocket } from "@/lib/api";

let idCounter = 0;
const uid = () => String(++idCounter);

export default function WsProvider({ children }: { children: React.ReactNode }) {
  const {
    setWsConnected, setAgents, updateAgent, addLog,
    incStat, setSystem,
  } = useDialerStore();
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
        // Reconnect after 3s
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
        incStat("answered");
        break;
      }
      case "voicemail_dropped": {
        incStat("voicemail");
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
        incStat("noAnswer");
        break;
      }
      case "amd_machine": {
        incStat("voicemail");
        break;
      }
      case "dialer_started": {
        setSystem({ dialer_running: true });
        break;
      }
      case "dialer_stopped": {
        setSystem({ dialer_running: false });
        break;
      }
    }
  };

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, []);

  return <>{children}</>;
}
