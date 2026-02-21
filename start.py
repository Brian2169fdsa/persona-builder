"""Entrypoint for Railway — reads PORT from environment."""
import os
import uvicorn

port = int(os.environ.get("PORT", "8001"))
print(f"Starting persona-builder on port {port}", flush=True)
uvicorn.run("app:app", host="0.0.0.0", port=port)
