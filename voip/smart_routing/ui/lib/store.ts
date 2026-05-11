import { create } from "zustand";

export type AgentStatus = "available" | "busy" | "offline";

export interface Agent {
  id: string;
  name: string;
  status: AgentStatus;
  mobile?: string;
  call_sid?: string | null;
}

export interface CallEntry {
  id: string;
  ts: string;
  event: string;
  msg?: string;
  call_sid?: string;
  agent?: string | number;
  to?: string;
  status?: string;
}

export interface SystemStatus {
  asterisk: boolean;
  webhook: boolean;
  ngrok: boolean;
  ngrok_url: string;
  dialer_running: boolean;
}

interface DialerStore {
  // Connection
  wsConnected: boolean;
  setWsConnected: (v: boolean) => void;

  // Agents
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  updateAgent: (id: string, patch: Partial<Agent>) => void;

  // Stats
  totalCalls: number;
  answered: number;
  voicemail: number;
  noAnswer: number;
  incStat: (key: "answered" | "voicemail" | "noAnswer") => void;

  // Call log
  callLog: CallEntry[];
  addLog: (entry: CallEntry) => void;

  // System
  system: SystemStatus;
  setSystem: (patch: Partial<SystemStatus>) => void;

  // Contacts
  totalContacts: number;
  setTotalContacts: (n: number) => void;

  // Active tab
  activeTab: string;
  setActiveTab: (t: string) => void;
}

export const useDialerStore = create<DialerStore>((set) => ({
  wsConnected: false,
  setWsConnected: (v) => set({ wsConnected: v }),

  agents: [],
  setAgents: (agents) => set({ agents }),
  updateAgent: (id, patch) =>
    set((s) => ({
      agents: s.agents.map((a) => (a.id === id ? { ...a, ...patch } : a)),
    })),

  totalCalls: 0,
  answered: 0,
  voicemail: 0,
  noAnswer: 0,
  incStat: (key) =>
    set((s) => ({ [key]: s[key] + 1, totalCalls: s.totalCalls + 1 } as any)),

  callLog: [],
  addLog: (entry) =>
    set((s) => ({ callLog: [entry, ...s.callLog].slice(0, 500) })),

  system: {
    asterisk: false,
    webhook: false,
    ngrok: false,
    ngrok_url: "",
    dialer_running: false,
  },
  setSystem: (patch) =>
    set((s) => ({ system: { ...s.system, ...patch } })),

  totalContacts: 0,
  setTotalContacts: (n) => set({ totalContacts: n }),

  activeTab: "dashboard",
  setActiveTab: (t) => set({ activeTab: t }),
}));
