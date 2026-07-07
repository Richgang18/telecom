"""
accent_demo.py — Real-time accent conversion demo
Browser mic → Deepgram STT → Cartesia TTS (American voice) → browser speakers

Run: python accent_demo.py
Open: http://localhost:8080
"""
from __future__ import annotations
import asyncio, json, os
from pathlib import Path
import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

DEEPGRAM_KEY = "f56a94291ae6b2329ee1afdd5e7d8d6f2aabb615"
CARTESIA_KEY = "sk_car_tVthKN3ZyTmFYxCuATc5XY"
# Tyler - Friendly Salesman (American male, sonic-3.5)
CARTESIA_VOICE_ID = "710feaa3-b550-42f3-b3eb-6f37f2a7cc0a"

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HTML = Path(__file__).parent / "index.html"


@app.get("/")
async def index():
    return HTMLResponse(HTML.read_text(encoding="utf-8"))


@app.get("/tts")
async def tts_page():
    """Text-to-American-voice demo — no microphone needed."""
    from tts_demo import TTS_HTML
    from fastapi.responses import HTMLResponse as HR
    return HR(TTS_HTML)


@app.post("/speak")
async def speak_endpoint(request: Request):
    """REST endpoint: POST JSON {text} → WAV audio in American voice."""
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
                "voice": {"mode": "id", "id": CARTESIA_VOICE_ID},
                "output_format": {"container": "wav", "encoding": "pcm_f32le", "sample_rate": 24000},
            },
        )
    if r.status_code != 200:
        return Response(r.text, status_code=500)
    return Response(content=r.content, media_type="audio/wav",
                    headers={"Cache-Control": "no-cache"})


@app.websocket("/stream")
async def stream(ws: WebSocket):
    """
    WebSocket pipeline:
    1. Receive raw PCM audio chunks from browser (16kHz, 16-bit, mono)
    2. Forward to Deepgram streaming STT via WebSocket
    3. Get transcript → send to Cartesia TTS REST API
    4. Send synthesized audio back to browser
    """
    await ws.accept()
    print("Client connected")

    import websockets as ws_lib

    dg_url = (
        "wss://api.deepgram.com/v1/listen"
        "?encoding=linear16&sample_rate=16000&channels=1"
        "&interim_results=false&smart_format=false"
        "&language=en-US&model=nova-2"
    )

    try:
        async with ws_lib.connect(
            dg_url,
            extra_headers={"Authorization": f"Token {DEEPGRAM_KEY}"},
        ) as dg:
            print("Deepgram connected")

            async def receive_transcripts():
                """Read Deepgram transcripts and synthesize via Cartesia."""
                async for msg in dg:
                    try:
                        data = json.loads(msg)
                        transcript = (
                            data.get("channel", {})
                                .get("alternatives", [{}])[0]
                                .get("transcript", "")
                                .strip()
                        )
                        if not transcript or data.get("is_final") is False:
                            continue

                        print(f"Transcript: {transcript}")

                        # Synthesize via Cartesia
                        async with httpx.AsyncClient(timeout=15) as client:
                            r = await client.post(
                                "https://api.cartesia.ai/tts/bytes",
                                headers={
                                    "X-API-Key": CARTESIA_KEY,
                                    "Cartesia-Version": "2024-06-10",
                                    "Content-Type": "application/json",
                                },
                                json={
                                    "transcript": transcript,
                                    "model_id": "sonic-3.5",
                                    "voice": {
                                        "mode": "id",
                                        "id": CARTESIA_VOICE_ID,
                                    },
                                    "output_format": {
                                        "container": "wav",
                                        "encoding": "pcm_f32le",
                                        "sample_rate": 24000,
                                    },
                                },
                            )

                        if r.status_code == 200:
                            audio = r.content
                            print(f"Synthesized {len(audio)} bytes")
                            # Send transcript text first so UI can show it
                            await ws.send_text(json.dumps({
                                "type": "transcript",
                                "text": transcript
                            }))
                            # Then send audio bytes
                            await ws.send_bytes(audio)
                        else:
                            print(f"Cartesia error: {r.status_code} {r.text[:200]}")

                    except Exception as e:
                        print(f"Transcript handler error: {e}")

            transcript_task = asyncio.create_task(receive_transcripts())

            try:
                while True:
                    msg = await ws.receive()
                    if msg["type"] == "websocket.receive":
                        if "bytes" in msg and msg["bytes"]:
                            await dg.send(msg["bytes"])
                        elif "text" in msg and msg["text"]:
                            ctrl = json.loads(msg["text"])
                            if ctrl.get("type") == "stop":
                                break
                    elif msg["type"] == "websocket.disconnect":
                        break
            finally:
                transcript_task.cancel()
                await dg.close()

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Stream error: {e}")
    finally:
        print("Stream closed")


if __name__ == "__main__":
    uvicorn.run("accent_demo:app", host="0.0.0.0", port=8082, reload=False)
