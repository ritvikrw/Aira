import urllib.request, json, ssl

ctx = ssl.create_default_context()
headers = {"X-API-Key": "sk_car_VDnR5SRdHqR7YsozgW6BDA", "Cartesia-Version": "2024-06-10", "Content-Type": "application/json"}

voices = [
    ("hi", "56e35e2d-6eb6-4226-ab8b-9776515a7094", "Kavita - Customer Care",  "नमस्ते! मैं आपकी कैसे मदद कर सकती हूँ?"),
    ("te", "cf061d8b-a752-4865-81a2-57570a6e0565", "Ramya - Graceful Host",    "నమస్కారం! మీకు ఎలా సహాయం చేయాలి?"),
    ("ta", "01d7796d-ac10-4ea3-8df0-3cc04f2d25ff", "Kavitha - Clear Comm",     "வணக்கம்! உங்களுக்கு எப்படி உதவலாம்?"),
    ("kn", "7c6219d2-e8d2-462c-89d8-7ecba7c75d65", "Divya - Joyful Narrator", "ನಮಸ್ಕಾರ! ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"),
    ("ml", "b426013c-002b-4e89-8874-8cd20b68373a", "Latha - Friendly Host",    "നമസ്കാരം! ഞാൻ എങ്ങനെ സഹായിക്കാം?"),
    ("en", "f8f5f1b2-f02d-4d8e-a40d-fd850a487b3d", "Kiara - Indian English",   "Hello! How can I help you today?"),
]

for model in ["sonic-3", "sonic-latest"]:
    print(f"\n=== {model} ===")
    for lang, voice_id, name, text in voices:
        body = json.dumps({
            "model_id": model,
            "transcript": text,
            "voice": {"mode": "id", "id": voice_id},
            "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 24000},
            "language": lang
        }).encode("utf-8")
        req = urllib.request.Request("https://api.cartesia.ai/tts/bytes", data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, context=ctx) as r:
                print(f"  OK  [{lang}] {name}: {len(r.read())} bytes")
        except urllib.error.HTTPError as e:
            print(f"  ERR [{lang}] {name}: {e.code} {e.read()[:60].decode()}")
