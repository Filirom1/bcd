import sys
import os
import socket
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.bcd_api.core import mdns


def test_normalize_hostname():
    assert mdns.normalize_hostname("EPH-BCD-001") == "eph-bcd-001"
    assert mdns.normalize_hostname("École  BCD!!") == "cole-bcd"
    assert mdns.normalize_hostname("---") == ""


def test_get_local_ip_uses_socket_address():
    socket_mod = __import__("socket")
    fake = type("Socket", (), {"connect": lambda self, address: None, "getsockname": lambda self: ("192.0.2.1", 0), "__enter__": lambda self: self, "__exit__": lambda *args: None})()
    with patch.object(socket_mod, "socket", return_value=fake):
        assert mdns.get_local_ip() == "192.0.2.1"


def test_get_server_port_falls_back_on_non_linux():
    with patch("sys.platform", "win32"):
        assert mdns.get_server_port(8888) == 8888


def test_get_server_port_linux_success():
    # Mock OS functions and /proc filesystem on Linux
    with patch("sys.platform", "linux"), \
         patch("os.getpid", return_value=123), \
         patch("os.listdir", return_value=["3", "4"]), \
         patch("os.readlink", side_effect=lambda path: "socket:[12345]" if "3" in path else "other"), \
         patch("builtins.open") as mock_open:

        # Mock reading /proc/net/tcp
        mock_file = MagicMock()
        mock_file.readlines.return_value = [
            "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode",
            "   0: 0100007F:22B8 00000000:0000 0A 00000000:00000000 00:00000000     0        0        0 12345"
        ]
        # local_address contains port 22B8 in hex, which is 8888 in decimal
        mock_open.return_value.__enter__.return_value = mock_file

        port = mdns.get_server_port(9999)
        assert port == 8888


def test_get_peers_various_configurations():
    # Setup global variables on mdns module
    mdns._peers = {
        "remote_service._bcd._tcp.local.": {
            "name": "remote_service._bcd._tcp.local.",
            "library_code": "remote_code",
            "host": "remote.local.",
            "addresses": ["192.168.1.10"],
            "port": 8000,
            "url": "http://192.168.1.10:8000",
        }
    }

    # 1. When not advertised locally
    mdns._service_info = None
    peers = mdns.get_peers()
    assert len(peers) == 1
    assert peers[0]["library_code"] == "remote_code"
    assert peers[0].get("local") is not True

    # 2. When advertised locally
    mock_info = MagicMock()
    mock_info.addresses = [socket.inet_aton("192.168.1.42")]
    mock_info.server = "local.local."
    mock_info.port = 8888
    mock_info.properties = {b"library_code": b"local_code"}

    mdns._service_info = mock_info
    mdns._own_service_name = "local_service"

    peers_with_local = mdns.get_peers()
    assert len(peers_with_local) == 2
    assert peers_with_local[0]["local"] is True
    assert peers_with_local[0]["library_code"] == "local_code"
    assert peers_with_local[0]["port"] == 8888
    assert peers_with_local[1]["library_code"] == "remote_code"

    # Clean up globals after test
    mdns._service_info = None
    mdns._own_service_name = None
    mdns._peers.clear()


def run(coro):
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_listener_and_async_add_service():
    listener = mdns._BCDServiceListener()

    # Test update_service simply calls add_service (mocking add_service)
    with patch.object(listener, "add_service") as mock_add:
        listener.update_service(None, "type", "name")
        mock_add.assert_called_once_with(None, "type", "name")

    # Test remove_service pops from peers
    mdns._peers = {"target_name": {"library_code": "target"}}
    listener.remove_service(None, "type", "target_name")
    assert "target_name" not in mdns._peers

    # Test add_service on own service name skips
    mdns._own_service_name = "my_own_service"
    with patch("asyncio.create_task") as mock_task:
        listener.add_service(None, "type", "my_own_service")
        mock_task.assert_not_called()

    # Test async add service resolution
    mock_info_instance = MagicMock()
    mock_info_instance.addresses = [socket.inet_aton("192.168.1.5")]
    mock_info_instance.port = 8000
    mock_info_instance.server = "peer.local."
    mock_info_instance.properties = {b"library_code": b"peer_code"}

    with patch("zeroconf.asyncio.AsyncServiceInfo", return_value=mock_info_instance) as mock_async_info:
        # Mock request to complete immediately
        mock_info_instance.async_request = AsyncMock()

        run(listener._async_add_service(None, mdns.BCD_SERVICE_TYPE, "remote_peer"))

        assert "remote_peer" in mdns._peers
        peer = mdns._peers["remote_peer"]
        assert peer["library_code"] == "peer_code"
        assert peer["addresses"] == ["192.168.1.5"]
        assert peer["port"] == 8000

    # Clean up
    mdns._peers.clear()
    mdns._own_service_name = None


def test_mdns_lifecycle():
    # 1. start_mdns with empty library code does nothing
    run(mdns.start_mdns("", 8888))
    assert mdns._zeroconf is None

    # 2. start_mdns with local IP resolution error
    with patch("src.bcd_api.core.mdns.get_local_ip", side_effect=OSError("No network")):
        run(mdns.start_mdns("my-lib", 8888))
        assert mdns._zeroconf is None

    # 3. Successful start, stop, and restart of mdns
    mock_async_zc = MagicMock()
    mock_async_zc.async_register_service = AsyncMock()
    mock_async_zc.async_unregister_service = AsyncMock()
    mock_async_zc.async_close = AsyncMock()

    with patch("src.bcd_api.core.mdns.get_local_ip", return_value="192.168.1.100"), \
         patch("zeroconf.asyncio.AsyncZeroconf", return_value=mock_async_zc), \
         patch("zeroconf.asyncio.AsyncServiceBrowser") as mock_browser_class:

        run(mdns.start_mdns("my-lib", 8888))

        assert mdns._zeroconf is mock_async_zc
        assert mdns._service_info is not None
        assert mdns._service_info.port == 8888
        assert mdns._own_service_name == f"BCD Library (my-lib).{mdns.BCD_SERVICE_TYPE}"

        mock_async_zc.async_register_service.assert_called_once_with(mdns._service_info)
        mock_browser_class.assert_called_once()

        # Restart mdns
        run(mdns.restart_mdns("new-lib", 9999))
        # Verify it unregistered old and registered new (or closed and opened new)
        assert mdns._service_info.port == 9999

        # Stop mdns
        mock_browser_instance = mock_browser_class.return_value
        mock_browser_instance.async_cancel = AsyncMock()
        mdns._browser = mock_browser_instance

        run(mdns.stop_mdns())

        assert mdns._zeroconf is None
        assert mdns._service_info is None
        assert mdns._browser is None
        assert mdns._listener is None
        assert mdns._own_service_name is None

