"""
tts_demo.py — Text to American Voice demo (no microphone needed)
Type any text → hear it in American English voice via Cartesia

Run: python tts_demo.py
Open: http://localhost:8082/tts
"""
from pathlib import Path
import httpx, uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware

CARTESIA_KEY  = "sk_car_tVthKN3ZyTmFYxCuATc5XY"
VOICE_ID      = "710feaa3-b550-42f3-b3eb-6f37f2a7cc0a"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TTS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>American Voice Demo</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#0a1628; color:#dfe6e9; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       min-height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:24px; }
h1 { font-size:26px; color:#e94560; margin-bottom:6px; }
.sub { color:#636e72; font-size:13px; margin-bottom:36px; text-align:center; }
.card { background:#16213e; border-radius:16px; padding:28px; width:100%; max-width:540px; }
.flow { display:flex; align-items:center; justify-content:center; gap:8px; margin-bottom:24px; flex-wrap:wrap; }
.step { background:#0a1628; border:1px solid #2d3436; border-radius:6px; padding:6px 12px; font-size:11px; color:#b2bec3; }
.step.done { border-color:#00b894; color:#00b894; }
.arrow { color:#636e72; }
textarea { width:100%; background:#0a1628; border:1px solid #2d3436; border-radius:8px; padding:14px;
           color:#dfe6e9; font-size:15px; resize:vertical; min-height:100px; outline:none; margin-bottom:16px; }
textarea:focus { border-color:#0984e3; }
#btnSpeak { width:100%; height:52px; border:none; border-radius:10px; background:#e94560; color:#fff;
            font-size:16px; font-weight:700; cursor:pointer; letter-spacing:0.5px; transition:background 0.2s; }
#btnSpeak:hover { background:#c73652; }
#btnSpeak:disabled { background:#2d3436; cursor:not-allowed; }
.result { margin-top:16px; background:#0f2d4a; border-radius:8px; padding:14px; display:none; }
.result .label { font-size:10px; color:#0984e3; font-weight:700; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }
.result .text { color:#dfe6e9; font-size:14px; }
.meta { margin-top:8px; font-size:11px; color:#636e72; }
.meta span { color:#fdcb6e; font-weight:700; }
</style>
</head>
<body>
<h1>🎙 American Voice Demo</h1>
<p class="sub">Type anything → hear it in a natural American English voice</p>
<div class="card">
  <div class="flow">
    <div class="step" id="s1">Your Text</div>
    <div class="arrow">→</div>
    <div class="step" id="s2">Cartesia TTS</div>
    <div class="arrow">→</div>
    <div class="step" id="s3">American Voice 🔊</div>
  </div>
  <textarea id="txt" placeholder="Type something here... e.g. 'Hello, I'm calling about your account status. How are you today?'">Hello! I'm calling to follow up on your inquiry. We'd love to help you get started today. Is this a good time to talk?</textarea>
  <button id="btnSpeak" onclick="speak()">🔊 SPEAK IN AMERICAN VOICE</button>
  <div class="result" id="result">
    <div class="label">🔊 American Voice Output</div>
    <div class="text" id="spokenText"></div>
    <div class="meta">Latency: <span id="latency">—</span> · Model: sonic-3.5 · Tyler (American male)</div>
  </div>
</div>
<script>
let t0;
async function speak() {
  const text = document.getElementById('txt').value.trim();
  if (!text) return;
  const btn = document.getElementById('btnSpeak');
  btn.disabled = true;
  btn.textContent = '⏳ Generating...';
  document.getElementById('s1').className = 'step done';
  document.getElementById('s2').className = 'step done';
  t0 = Date.now();
  try {
    const r = await fetch('/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    });
    if (!r.ok) { alert('Error: ' + await r.text()); return; }
    const elapsed = Date.now() - t0;
    const blob = await r.blob();
    const url  = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play();
    document.getElementById('s3').className = 'step done';
    document.getElementById('spokenText').textContent = text;
    document.getElementById('latency').textContent = elapsed + 'ms';
    document.getElementById('result').style.display = 'block';
    audio.onended = () => URL.revokeObjectURL(url);
  } catch(e) {
    alert('Failed: ' + e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '🔊 SPEAK IN AMERICAN VOICE';
    setTimeout(() => {
      document.querySelectorAll('.step').forEach(s => s.className = 'step');
    }, 3000);
  }
}
document.getElementById('txt').addEventListener('keydown', e => {
  if (e.key === 'Enter' && e.ctrlKey) speak();
});
</script>
</body>
</html>"""


@app.get("/tts")
async def tts_page():
    return HTMLResponse(TTS_HTML)


@app.post("/speak")
async def speak(request: Request):
    body = await request.json()
    text = body.get("text", "").strip()
    if not text:
        return Response("No text", status_code=400)

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://api.cartesia.ai/tts/bytes",
            headers={
                "X-API-Key": CARTESIA_KEY,
                "Cartesia-Version": "2024-06-10",
                "Content-Type": "application/json",
            },
            json={
                "transcript": text,
                "model_id": "sonic-3.5",
                "voice": {"mode": "id", "id": VOICE_ID},
                "output_format": {
                    "container": "wav",
                    "encoding": "pcm_f32le",
                    "sample_rate": 24000,
                },
            },
        )

    if r.status_code != 200:
        return Response(r.text, status_code=500)

    return Response(
        content=r.content,
        media_type="audio/wav",
        headers={"Cache-Control": "no-cache"},
    )
