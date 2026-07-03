import urllib.request, json, ssl

ctx = ssl.create_default_context()
headers = {"X-API-Key": "sk_car_VDnR5SRdHqR7YsozgW6BDA", "Cartesia-Version": "2024-06-10", "Content-Type": "application/json"}

for model in ["sonic-2", "sonic", "sonic-english", "sonic-multilingual", "sonic-2-2025-10", "upbeat-moon"]:
    body = json.dumps({
        "model_id": model,
        "transcript": "Hello",
        "voice": {"mode": "id", "id": "f8f5f1b2-f02d-4d8e-a40d-fd850a487b3d"},
        "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000},
        "language": "en"
    }).encode()
    req = urllib.request.Request("https://api.cartesia.ai/tts/bytes", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print(f"OK  model={model}: {len(r.read())} bytes")
    except urllib.error.HTTPError as e:
        print(f"ERR model={model}: {e.code} {e.read()[:80].decode()}")
