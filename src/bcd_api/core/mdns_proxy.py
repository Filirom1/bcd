"""Minimal peer-only API used by the portable CLIENT_ONLY launcher.

This is not the BCD API and does not initialize a database. It keeps the same
mDNS peer browser used by the normal server and exposes only the existing
``/api/v1/collections/peers`` endpoint to the local Kids client.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.bcd_api.api.v1.collections import router as collections_router
from src.bcd_api.core import mdns


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Start the shared mDNS browser and stop it with the peer-only app."""
    await mdns.start_peer_browser()
    yield
    await mdns.stop_mdns()


app = FastAPI(
    title="BCD Client Discovery",
    description="Peer discovery endpoint used by BCD Kids in client-only mode.",
    lifespan=_lifespan,
)
app.include_router(collections_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health endpoint used to verify that the peer-only app is available."""
    return {"status": "healthy", "mode": "client-only"}
