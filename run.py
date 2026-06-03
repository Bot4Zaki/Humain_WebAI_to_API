#!/usr/bin/env python3
"""
Entrypoint: start the humain-webai-to-api FastAPI server.

Usage:
    python run.py
    # or
    uvicorn app.main:app --host 127.0.0.1 --port 8100
"""

import uvicorn

from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )
