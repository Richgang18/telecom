"""List available Cartesia voices to find American English."""
import httpx

r = httpx.get(
    "https://api.cartesia.ai/voices",
    headers={"X-API-Key": "sk_car_tVthKN3ZyTmFYxCuATc5XY", "Cartesia-Version": "2024-06-10"},
    timeout=10,
)
print(f"HTTP {r.status_code}")
if r.status_code == 200:
    voices = r.json()
    en_voices = [v for v in voices if
                 "en" in str(v.get("language","")).lower() or
                 "english" in str(v.get("name","")).lower()]
    print(f"\nFound {len(en_voices)} English voices (first 15):\n")
    for v in en_voices[:15]:
        print(f"  ID:   {v.get('id')}")
        print(f"  Name: {v.get('name')}")
        print(f"  Lang: {v.get('language','')}")
        print()
else:
    print(r.text[:500])
