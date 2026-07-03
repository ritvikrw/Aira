import urllib.request, json, ssl

ctx = ssl.create_default_context()
headers = {"X-API-Key": "sk_car_VDnR5SRdHqR7YsozgW6BDA", "Cartesia-Version": "2024-06-10", "Content-Type": "application/json"}

# Check what language the Hindi voice supports and try different models
voice_id = "56e35e2d-6eb6-4226-ab8b-9776515a7094"
models = ["sonic-2", "sonic-2-2026", "sonic-3", "sonic-2-latest", "sonic-latest"]

for model in models:
    body = json.dumps({
        "model_id": model,
        "transcript": "नमस्ते",
        "voice": {"mode": "id", "id": voice_id},
        "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000},
        "language": "hi"
    }).encode("utf-8")
    req = urllib.request.Request("https://api.cartesia.ai/tts/bytes", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print(f"OK  model={model}: {len(r.read())} bytes")
    except urllib.error.HTTPError as e:
        msg = e.read()[:80].decode()
        print(f"ERR model={model}: {e.code} {msg}")

# Try without language param
print("\n--- Without language param ---")
for voice, lang_name in [("56e35e2d-6eb6-4226-ab8b-9776515a7094","hi"), ("cf061d8b-a752-4865-81a2-57570a6e0565","te")]:
    body = json.dumps({
        "model_id": "sonic-2",
        "transcript": "नमस्ते" if lang_name=="hi" else "నమస్కారం",
        "voice": {"mode": "id", "id": voice},
        "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000}
    }).encode("utf-8")
    req = urllib.request.Request("https://api.cartesia.ai/tts/bytes", data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx) as r:
            print(f"OK  [{lang_name}] no-lang-param: {len(r.read())} bytes")
    except urllib.error.HTTPError as e:
        print(f"ERR [{lang_name}] no-lang-param: {e.code} {e.read()[:80].decode()}")
