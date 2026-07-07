"""Test Cartesia TTS with current sonic-3.5 model."""
import httpx

CARTESIA_KEY = "sk_car_tVthKN3ZyTmFYxCuATc5XY"
VOICE_ID     = "710feaa3-b550-42f3-b3eb-6f37f2a7cc0a"  # Tyler - Friendly Salesman

print("Testing Cartesia sonic-3.5...")
r = httpx.post(
    "https://api.cartesia.ai/tts/bytes",
    headers={
        "X-API-Key": CARTESIA_KEY,
        "Cartesia-Version": "2024-06-10",
        "Content-Type": "application/json",
    },
    json={
        "transcript": "Hello, this is a test of the American accent conversion system.",
        "model_id": "sonic-3.5",
        "voice": {"mode": "id", "id": VOICE_ID},
        "output_format": {
            "container": "wav",
            "encoding": "pcm_f32le",
            "sample_rate": 24000,
        },
    },
    timeout=15,
)
print(f"HTTP {r.status_code}")
if r.status_code == 200:
    with open("test_output.wav", "wb") as f:
        f.write(r.content)
    print(f"SUCCESS — {len(r.content):,} bytes → test_output.wav")
else:
    print(f"Error: {r.text[:300]}")
    # Try without specifying voice to get a default
    print("\nTrying with default voice...")
    r2 = httpx.post(
        "https://api.cartesia.ai/tts/bytes",
        headers={"X-API-Key": CARTESIA_KEY, "Cartesia-Version": "2024-06-10", "Content-Type": "application/json"},
        json={
            "transcript": "Hello, testing American voice.",
            "model_id": "sonic-3.5",
            "voice": {"mode": "id", "id": "a0e99841-438c-4a64-b679-ae501e7d6091"},  # Barbershop man
            "output_format": {"container": "wav", "encoding": "pcm_f32le", "sample_rate": 24000},
        },
        timeout=15,
    )
    print(f"HTTP {r2.status_code}")
    if r2.status_code == 200:
        with open("test_output.wav", "wb") as f:
            f.write(r2.content)
        print(f"SUCCESS with fallback voice — {len(r2.content):,} bytes")
    else:
        print(r2.text[:300])
