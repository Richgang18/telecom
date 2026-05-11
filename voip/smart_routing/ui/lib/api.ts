const BASE = "http://localhost:5000";

export async function fetchStatus() {
  const r = await fetch(`${BASE}/api/status`);
  return r.json();
}

export async function fetchConfig() {
  const r = await fetch(`${BASE}/api/config`);
  return r.json();
}

export async function saveConfig(body: object) {
  const r = await fetch(`${BASE}/api/config`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

export async function startDialer() {
  const r = await fetch(`${BASE}/api/dialer/start`, { method: "POST" });
  return r.json();
}

export async function stopDialer() {
  const r = await fetch(`${BASE}/api/dialer/stop`, { method: "POST" });
  return r.json();
}

export async function detectNgrok() {
  const r = await fetch(`${BASE}/api/ngrok/detect`);
  return r.json();
}

export async function fetchCallLog() {
  const r = await fetch(`${BASE}/api/call-log`);
  return r.json();
}

export function createWebSocket(onMessage: (data: any) => void, onOpen?: () => void, onClose?: () => void) {
  const ws = new WebSocket("ws://localhost:5000/ws");
  ws.onopen = () => onOpen?.();
  ws.onmessage = (e) => {
    try { onMessage(JSON.parse(e.data)); } catch {}
  };
  ws.onclose = () => onClose?.();
  return ws;
}
