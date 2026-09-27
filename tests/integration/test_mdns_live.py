"""Live mDNS integration tests for the Python and standalone Godot clients.

These tests intentionally use a real zeroconf advertisement rather than a
synthetic DNS packet.  They are marked ``external`` because multicast can be
disabled by a CI runner or a developer's network namespace.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from zeroconf import ServiceInfo, Zeroconf

from src.bcd_api.core import mdns
from src.bcd_api.core.runner import _start_mdns_proxy_thread

ROOT = Path(__file__).resolve().parents[2]


class _LiveMdnsAdvertiser:
    """A real DNS-SD advertiser kept alive for the duration of one test."""

    def __init__(self, address: str) -> None:
        token = uuid.uuid4().hex[:10]
        self.address = address
        self.library_code = f"Live mDNS {token}"
        self.port = self._find_port(address)
        self.service_name = f"BCD Live ({token}).{mdns.BCD_SERVICE_TYPE}"
        self.server_name = f"bcd-live-{token}.local."
        self._zeroconf: Zeroconf | None = None
        self._service_info: ServiceInfo | None = None

    @staticmethod
    def _find_port(address: str) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind((address, 0))
            return int(probe.getsockname()[1])

    @property
    def url(self) -> str:
        return f"http://{self.address}:{self.port}"

    def start(self) -> None:
        self._zeroconf = Zeroconf(interfaces=[self.address])
        self._service_info = ServiceInfo(
            type_=mdns.BCD_SERVICE_TYPE,
            name=self.service_name,
            addresses=[socket.inet_aton(self.address)],
            port=self.port,
            properties={
                "library_code": self.library_code,
                "path": "/",
                "description": "BCD live mDNS integration test",
            },
            server=self.server_name,
        )
        self._zeroconf.register_service(self._service_info)

    def stop(self) -> None:
        if self._zeroconf is None:
            return
        try:
            if self._service_info is not None:
                self._zeroconf.unregister_service(self._service_info)
        finally:
            self._zeroconf.close()
            self._zeroconf = None
            self._service_info = None


def _select_multicast_address() -> str:
    """Return a non-loopback IPv4 address usable by both clients."""
    try:
        address = mdns.get_local_ip()
    except OSError as exc:
        pytest.skip(f"mDNS integration requires an IPv4 route: {exc}")

    if address.startswith(("127.", "169.254.")) or address == "0.0.0.0":
        pytest.skip(f"mDNS integration requires a non-loopback IPv4 interface, got {address}")
    return address


@pytest.fixture
def live_mdns_advertiser() -> _LiveMdnsAdvertiser:
    advertiser = _LiveMdnsAdvertiser(_select_multicast_address())
    try:
        advertiser.start()
    except (OSError, RuntimeError, ValueError) as exc:
        advertiser.stop()
        pytest.skip(f"mDNS is unavailable in this network namespace: {exc}")

    try:
        yield advertiser
    finally:
        advertiser.stop()


async def _wait_for_peer(predicate, timeout: float = 8.0) -> list[mdns.PeerInfo]:
    """Poll the real Python peer registry until a matching service appears."""
    deadline = time.monotonic() + timeout
    peers: list[mdns.PeerInfo] = []
    while time.monotonic() < deadline:
        peers = mdns.get_peers()
        if any(predicate(peer) for peer in peers):
            return peers
        await asyncio.sleep(0.1)
    return peers


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.slow
@pytest.mark.asyncio
async def test_python_peer_browser_detects_real_mdns_advertisement(live_mdns_advertiser):
    """The Python mDNS browser resolves a real PTR/SRV/TXT/A announcement."""
    await mdns.stop_mdns()
    try:
        assert await mdns.start_peer_browser()
        peers = await _wait_for_peer(
            lambda peer: peer.get("library_code") == live_mdns_advertiser.library_code
        )
        matching = [
            peer for peer in peers if peer.get("library_code") == live_mdns_advertiser.library_code
        ]
        assert matching, f"Python did not detect {live_mdns_advertiser.service_name}: {peers!r}"
        peer = matching[0]
        assert peer["url"] == live_mdns_advertiser.url
        assert peer["port"] == live_mdns_advertiser.port
        assert live_mdns_advertiser.address in peer["addresses"]
    finally:
        await mdns.stop_mdns()


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.slow
def test_client_only_proxy_exposes_real_mdns_peer(live_mdns_advertiser):
    """The CLIENT_ONLY loopback proxy exposes the live Python peer snapshot."""
    server, thread = _start_mdns_proxy_thread(_find_loopback_port())
    assert server is not None
    assert thread is not None

    try:
        endpoint = f"http://127.0.0.1:{server.config.port}/api/v1/collections/peers"
        deadline = time.monotonic() + 8.0
        peers = []
        while time.monotonic() < deadline:
            try:
                with urlopen(endpoint, timeout=0.5) as response:
                    assert response.status == 200
                    peers = json.loads(response.read().decode("utf-8"))
            except (OSError, URLError, json.JSONDecodeError):
                peers = []

            if any(
                isinstance(peer, dict)
                and peer.get("library_code") == live_mdns_advertiser.library_code
                for peer in peers
            ):
                break
            time.sleep(0.1)

        matching = [
            peer
            for peer in peers
            if isinstance(peer, dict)
            and peer.get("library_code") == live_mdns_advertiser.library_code
        ]
        assert matching, f"CLIENT_ONLY proxy did not expose the live mDNS peer: {peers!r}"
        assert matching[0]["url"] == live_mdns_advertiser.url
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        assert not thread.is_alive(), "CLIENT_ONLY mDNS proxy did not stop"


def _find_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _find_godot() -> str | None:
    configured = os.environ.get("GODOT_BIN")
    if configured:
        return configured if Path(configured).is_file() else shutil.which(configured)
    return shutil.which("godot") or shutil.which("godot4")


@pytest.mark.integration
@pytest.mark.external
@pytest.mark.slow
def test_standalone_godot_detects_real_mdns_advertisement(live_mdns_advertiser, tmp_path):
    """Pure Godot discovery sees a live advertisement without the Python proxy."""
    godot = _find_godot()
    if godot is None:
        pytest.skip("Godot is not installed; standalone live discovery is opt-in")

    env = os.environ.copy()
    env["BCD_GODOT_TESTS"] = "1"
    env["BCD_MDNS_EXPECTED_LIBRARY"] = live_mdns_advertiser.library_code
    env["BCD_MDNS_EXPECTED_URL"] = live_mdns_advertiser.url
    # The native test must not accidentally use the CLIENT_ONLY proxy path.
    env.pop("BCD_MDNS_PROXY_PORT", None)
    env.setdefault("GODOT_SILENCE_ROOT_WARNING", "1")
    for variable in (
        "HOME",
        "XDG_DATA_HOME",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_STATE_HOME",
    ):
        directory = tmp_path / variable.lower()
        directory.mkdir()
        env[variable] = str(directory)

    command = [
        godot,
        "--headless",
        "--path",
        str(ROOT / "bcd_kids"),
        "--script",
        "res://tests/mdns_live_integration.gd",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"Godot live mDNS test timed out: {exc}")

    output = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, (
        "Standalone Godot did not detect the live mDNS advertisement "
        f"(exit {result.returncode}):\n{output}"
    )
    assert "Godot detected the live mDNS advertiser" in output
