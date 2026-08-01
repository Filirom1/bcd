"""mDNS service advertisement and peer discovery for BCD instances.

Registers the BCD service so users can reach it at <library_code>.local
without manual DNS or hosts-file configuration, and browses the local
network for other BCD instances.

Service type: ``_bcd._tcp.local.`` (scoped to BCD only, replacing the
previous generic ``_http._tcp.local.``)

Requires the 'zeroconf' package. If it is not installed the module logs a
warning and all public functions become no-ops so the server starts normally.
"""

import logging
import re
import socket
from typing import TypedDict, NotRequired

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────
BCD_SERVICE_TYPE = "_bcd._tcp.local."

# ── Module-level singletons ──────────────────────────────────────────────────
_zeroconf = None                        # AsyncZeroconf instance
_service_info = None                    # ServiceInfo for our own advertisement
_browser = None                         # AsyncServiceBrowser for peer discovery
_listener = None                        # ServiceListener instance (kept alive)
_own_service_name: str | None = None   # used to exclude self from peer list
_peers: dict[str, "PeerInfo"] = {}     # mDNS service name → PeerInfo


# ── Public types ─────────────────────────────────────────────────────────────
class PeerInfo(TypedDict):
    """Snapshot of a discovered BCD peer."""
    name: str            # full mDNS service name (internal key)
    library_code: str    # raw library_code from the peer's TXT record
    host: str            # mDNS FQDN, e.g. "eph-bcd-001.local."
    addresses: list[str] # IPv4 addresses
    port: int
    url: str             # convenience http://<ip>:<port>
    local: NotRequired[bool]          # True only for this instance (always first in list)


def normalize_hostname(library_code: str) -> str:
    """Convert a library_code into a valid mDNS hostname component.

    Rules:
    - Lowercase
    - Replace any character that is not [a-z0-9-] with '-'
    - Collapse multiple consecutive dashes into one
    - Strip leading/trailing dashes

    Examples:
        "bcd"          -> "bcd"
        "EPH-BCD-001"  -> "eph-bcd-001"
        "École BCD"    -> "cole-bcd"
    """
    hostname = library_code.lower()
    hostname = re.sub(r"[^a-z0-9-]", "-", hostname)
    hostname = re.sub(r"-{2,}", "-", hostname)
    hostname = hostname.strip("-")
    return hostname


def get_local_ip() -> str:
    """Discover the machine's LAN IP address via a connect-trick.

    Opens a UDP socket toward 8.8.8.8:80 (no packet is actually sent) and
    reads back the local address the OS chose for that route.

    Returns:
        The LAN IP string, e.g. "192.168.1.42".

    Raises:
        OSError: If the socket operation fails (no network interface).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


def get_server_port(fallback: int) -> int:
    """Detect the TCP port this process is currently listening on.

    Reads /proc/self/fd (socket inodes) and /proc/net/tcp[6] (LISTEN rows)
    on Linux.  Falls back to *fallback* on non-Linux systems or on any error.

    Args:
        fallback: Port number to return when detection fails.

    Returns:
        Detected listening port, or *fallback*.
    """
    import os
    import sys

    if sys.platform != "linux":
        return fallback

    pid = os.getpid()
    fd_dir = f"/proc/{pid}/fd"

    # Collect socket inodes owned by this process
    socket_inodes: set[int] = set()
    try:
        for fd_name in os.listdir(fd_dir):
            try:
                link = os.readlink(f"{fd_dir}/{fd_name}")
                if link.startswith("socket:["):
                    socket_inodes.add(int(link[8:-1]))
            except (OSError, ValueError):
                pass
    except OSError:
        return fallback

    if not socket_inodes:
        return fallback

    # Search /proc/net/tcp[6] for LISTEN sockets matching our inodes
    for tcp_file in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(tcp_file) as fh:
                for line in fh.readlines()[1:]:
                    parts = line.split()
                    if len(parts) < 10:
                        continue
                    state, local_addr, inode_str = parts[3], parts[1], parts[9]
                    if state == "0A" and int(inode_str) in socket_inodes:
                        port = int(local_addr.split(":")[1], 16)
                        if port > 0:
                            return port
        except (OSError, ValueError):
            pass

    return fallback


# ── Peer registry ─────────────────────────────────────────────────────────────
def get_peers() -> list[PeerInfo]:
    """Return a snapshot of currently visible BCD peers on the LAN.

    This instance appears first (marked ``local=True``) so that clients can
    highlight it and suggest it as the default.  Remote peers follow in
    discovery order.

    Returns:
        A new list of :class:`PeerInfo` dicts (empty when mDNS is not
        running or no peers have been found yet).
    """
    peers = list(_peers.values())

    if _service_info is not None and _own_service_name is not None:
        addresses = [
            socket.inet_ntoa(addr)
            for addr in _service_info.addresses
            if len(addr) == 4
        ]
        if addresses:
            props: dict[str, str] = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode() if isinstance(v, bytes) else (v or "")
                )
                for k, v in (_service_info.properties or {}).items()
            }
            port = _service_info.port or 0
            self_peer: PeerInfo = {
                "name": _own_service_name,
                "library_code": props.get("library_code", ""),
                "host": _service_info.server or "",
                "addresses": addresses,
                "port": port,
                "url": f"http://{addresses[0]}:{port}",
                "local": True,
            }
            peers = [self_peer] + peers

    return peers


# ── Internal Zeroconf listener ────────────────────────────────────────────────
class _BCDServiceListener:
    """Zeroconf ``ServiceListener`` that keeps ``_peers`` up-to-date.

    ``AsyncServiceBrowser`` calls these methods from the event-loop thread
    whenever a ``_bcd._tcp.local.`` service appears, changes, or goes away.

    ``zc.get_service_info()`` (sync) is safe to call here because it does
    not block the asyncio loop — it queries the local Zeroconf cache.
    """

    def add_service(self, zc, type_: str, name: str) -> None:
        """Called when a service is discovered. Schedules async resolution."""
        import asyncio

        logger.debug("add_service called: name=%s, own=%s", name, _own_service_name)

        if name == _own_service_name:
            logger.debug("Skipping own service: %s", name)
            return  # never list ourselves

        # Schedule async resolution
        asyncio.create_task(self._async_add_service(zc, type_, name))

    async def _async_add_service(self, zc, type_: str, name: str) -> None:
        """Async resolution of service info."""
        from zeroconf.asyncio import AsyncServiceInfo

        try:
            logger.debug("Resolving service info for: %s", name)
            info = AsyncServiceInfo(type_, name)
            await info.async_request(zc, 3000)
        except Exception as exc:
            logger.warning("async_request(%s) failed: %s", name, exc)
            return

        if not info.addresses:
            logger.warning("No addresses returned for %s — ignoring.", name)
            return

        # Only IPv4 for now (len==4 bytes); skip link-local / IPv6
        addresses = [
            socket.inet_ntoa(addr)
            for addr in info.addresses
            if len(addr) == 4
        ]

        if not addresses:
            logger.warning("No IPv4 addresses for %s — ignoring.", name)
            return

        # TXT record values are bytes in older zeroconf versions
        props: dict[str, str] = {
            (k.decode() if isinstance(k, bytes) else k): (
                v.decode() if isinstance(v, bytes) else (v or "")
            )
            for k, v in (info.properties or {}).items()
        }

        library_code = props.get("library_code", "")
        primary_ip = addresses[0]
        port = info.port or 0

        peer: PeerInfo = {
            "name": name,
            "library_code": library_code,
            "host": info.server or "",
            "addresses": addresses,
            "port": port,
            "url": f"http://{primary_ip}:{port}",
        }

        _peers[name] = peer
        logger.info(
            "BCD peer discovered: library_code=%r  url=%s  addresses=%s",
            library_code,
            peer["url"],
            addresses,
        )

    def remove_service(self, zc, type_: str, name: str) -> None:
        peer = _peers.pop(name, None)
        if peer:
            logger.info(
                "BCD peer lost: library_code=%r  host=%s",
                peer.get("library_code") or name,
                peer.get("host"),
            )

    def update_service(self, zc, type_: str, name: str) -> None:
        # Re-use add logic; _peers[name] is simply overwritten
        self.add_service(zc, type_, name)


# ── Public lifecycle API ──────────────────────────────────────────────────────
async def start_mdns(library_code: str, port: int) -> None:
    """Register the BCD mDNS service and start browsing for peers.

    Does nothing (logs a warning) if:
    - *zeroconf* is not installed
    - *library_code* is falsy after normalisation
    - No LAN IP can be determined

    Both advertisement and discovery use ``_bcd._tcp.local.`` so that only
    BCD nodes are found, regardless of other HTTP services on the network.

    Args:
        library_code: Raw library code string from settings.
        port: HTTP port the server is listening on.
    """
    global _zeroconf, _service_info, _browser, _listener, _own_service_name

    try:
        from zeroconf import ServiceInfo
        from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf
    except ImportError:
        logger.warning(
            "zeroconf package not installed — mDNS advertisement disabled. "
            "Install it with: pip install zeroconf"
        )
        return

    hostname = normalize_hostname(library_code) if library_code else ""
    if not hostname:
        logger.warning("library_code is empty after normalisation — mDNS skipped.")
        return

    try:
        local_ip = get_local_ip()
    except OSError as exc:
        logger.warning("Cannot determine LAN IP for mDNS: %s — mDNS skipped.", exc)
        return

    service_name = f"BCD Library ({hostname}).{BCD_SERVICE_TYPE}"
    fqdn = f"{hostname}.local."

    _own_service_name = service_name

    _service_info = ServiceInfo(
        type_=BCD_SERVICE_TYPE,
        name=service_name,
        addresses=[socket.inet_aton(local_ip)],
        port=port,
        properties={
            "library_code": library_code,   # ← lets peers identify us w/o HTTP
            "path": "/",
            "description": "BCD Library Management System",
        },
        server=fqdn,
    )

    # ── Advertise ourselves ───────────────────────────────────────────────────
    try:
        _zeroconf = AsyncZeroconf()
        await _zeroconf.async_register_service(_service_info)
        logger.info(
            "mDNS registered: %s:%d → %s  (service: %s)",
            fqdn,
            port,
            local_ip,
            service_name,
        )
    except Exception as exc:
        logger.warning("mDNS registration failed: %s", exc)
        _zeroconf = None
        _service_info = None
        _own_service_name = None
        return

    # ── Browse for other BCD instances ────────────────────────────────────────
    _peers.clear()
    try:
        # Keep listener reference to prevent garbage collection
        _listener = _BCDServiceListener()
        # AsyncServiceBrowser takes the underlying *sync* Zeroconf instance
        _browser = AsyncServiceBrowser(
            _zeroconf.zeroconf,
            BCD_SERVICE_TYPE,
            listener=_listener,
        )
        logger.info("mDNS peer discovery started  (type: %s)", BCD_SERVICE_TYPE)
    except Exception as exc:
        logger.warning("mDNS peer discovery failed to start: %s", exc)
        _browser = None
        _listener = None


async def stop_mdns() -> None:
    """Unregister the mDNS service, stop peer browsing, and close Zeroconf."""
    global _zeroconf, _service_info, _browser, _listener, _own_service_name

    if _zeroconf is None:
        return

    try:
        if _browser is not None:
            await _browser.async_cancel()
        if _service_info is not None:
            await _zeroconf.async_unregister_service(_service_info)
        await _zeroconf.async_close()
        logger.info("mDNS service unregistered and peer discovery stopped.")
    except Exception as exc:
        logger.warning("Error stopping mDNS: %s", exc)
    finally:
        _zeroconf = None
        _service_info = None
        _browser = None
        _listener = None
        _own_service_name = None
        _peers.clear()


async def restart_mdns(library_code: str | None, port: int) -> None:
    """Stop any running mDNS registration then start a new one.

    If *library_code* is None or empty the service is only stopped.

    Args:
        library_code: New library code (may be None to clear mDNS).
        port: HTTP port the server is listening on.
    """
    await stop_mdns()
    if library_code:
        await start_mdns(library_code, port)
