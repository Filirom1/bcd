extends SceneTree

# This script is launched by tests/integration/test_mdns_live.py while a real
# Python DNS-SD advertiser is running.  It deliberately bypasses the Python
# client-only proxy: this is the standalone/native Godot discovery path.
const MDNS_SCRIPT = preload("res://src/utils/MdnsDiscovery.gd")


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var expected_library := OS.get_environment("BCD_MDNS_EXPECTED_LIBRARY")
	var expected_url := OS.get_environment("BCD_MDNS_EXPECTED_URL")
	if expected_library.is_empty() or expected_url.is_empty():
		push_error("Live mDNS test requires BCD_MDNS_EXPECTED_LIBRARY and BCD_MDNS_EXPECTED_URL")
		quit(2)
		return

	var discovery = MDNS_SCRIPT.new()
	var peers: Array = await discovery.discover(5.0)
	print("Godot live mDNS peers: " + JSON.stringify(peers))

	for peer_variant in peers:
		if not (peer_variant is Dictionary):
			continue
		var peer: Dictionary = peer_variant
		if (
			str(peer.get("library_code", "")) == expected_library
			and str(peer.get("url", "")) == expected_url
		):
			print("Godot detected the live mDNS advertiser")
			quit(0)
			return

	push_error("Godot did not detect the expected live mDNS advertiser")
	quit(1)
