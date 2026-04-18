"""Collections API endpoints for peer discovery."""

from fastapi import APIRouter
from ...core.mdns import get_peers

router = APIRouter(prefix="/collections", tags=["collections"])


@router.get("/peers")
async def list_peers():
    """Return BCD instances currently visible on the local network.

    Uses real-time mDNS peer registry maintained by AsyncServiceBrowser.
    Peers appear/disappear automatically as mDNS advertisements are received.

    Returns:
        List of PeerInfo dicts with library_code, url, addresses, etc.
    """
    return get_peers()
