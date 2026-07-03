"""Startup script: loads .env then launches uvicorn on port 8000."""
import os, sys

# Load .env
env_path = os.path.join(os.path.dirname(__file__), "backend", ".env")
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# DATABASE_URL from .env already has correct port (5434 = Docker postgres)
os.environ["CHROMA_PERSIST_PATH"] = os.path.join(os.path.dirname(__file__), "chroma_data")
os.environ["UPLOAD_DIR"] = os.path.join(os.path.dirname(__file__), "uploads")

# Point to the API directory
api_dir = os.path.join(os.path.dirname(__file__), "backend", "api")
sys.path.insert(0, api_dir)
os.chdir(api_dir)

import uvicorn
uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
