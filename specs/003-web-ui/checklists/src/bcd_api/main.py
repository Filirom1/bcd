"""
BCD Library Management System - FastAPI Server
Serves both the REST API and the web UI
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

# Initialize FastAPI app
app = FastAPI(
    title="BCD Library Management System",
    description="RESTful API for school library management",
    version="1.0.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8888", "http://127.0.0.1:8888"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Templates for htmx fragments
templates = Jinja2Templates(directory=str(BASE_DIR / "src" / "bcd_web" / "templates"))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "bcd-api"}

# API routes will be added in later phases
# For now, we just need to serve the web UI

# Mount static files - serve web UI assets at /static
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "src" / "bcd_web")), name="static")

# Serve index.html at root - must be last mount to catch all remaining routes
@app.get("/", response_class=HTMLResponse)
async def serve_spa(request: Request):
    """Serve the SPA entry point"""
    index_path = BASE_DIR / "src" / "bcd_web" / "index.html"
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
