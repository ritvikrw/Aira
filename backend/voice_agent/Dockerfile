FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download all plugin model files (Silero VAD + turn detector ONNX weights).
# Baking them into the image layer prevents a download on every cold start.
RUN python -m livekit.agents download-files

COPY . .

CMD ["python", "main.py", "start"]
