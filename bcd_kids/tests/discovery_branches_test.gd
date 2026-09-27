extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const HTTP_SERVER = preload("res://tests/api_test_server.gd")

var _test := SUPPORT.new()
var _server: Node
var _screen: Control
var _gs: Node
var _settings: Node
var _previous_base_url := ""
var _previous_library_name := ""
var _previous_last_url := ""
var _previous_last_name := ""


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	_gs = get_root().get_node("GS")
	_settings = get_root().get_node("Settings")
	_previous_base_url = str(_gs.get("base_url"))
	_previous_library_name = str(_gs.get("library_name"))
	_previous_last_url = str(_settings.get("last_server_url"))
	_previous_last_name = str(_settings.get("last_library_name"))

	_server = HTTP_SERVER.new()
	get_root().add_child(_server)
	if not _server.call("start"):
		_test.expect(false, "Discovery HTTP fixture starts")
		_test.finish(self)
		return
	await _test.wait_frames(self)

	_screen = load("res://src/screens/SServerDiscovery.tscn").instantiate()
	_screen.set("_discovering", true)
	get_root().add_child(_screen)
	await _test.wait_frames(self, 5)
	_gs.base_url = "http://127.0.0.1:%d/api/v1" % int(_server.get("port"))

	await _test_proxy_response_branches()
	await _test_health_response_branches()
	await _test_auth_connection_branches()
	_test_peer_merging()

	if is_instance_valid(_screen):
		_screen.queue_free()
	await _test.wait_frames(self, 3)
	_server.call("stop")
	_server.queue_free()
	_gs.base_url = _previous_base_url
	_gs.library_name = _previous_library_name
	_settings.last_server_url = _previous_last_url
	_settings.last_library_name = _previous_last_name
	_test.finish(self)


func _clear_fixture() -> void:
	_server.call("clear_routes")
	_server.get("requests").clear()


func _enqueue_json(path: String, status_code: int, value) -> void:
	_server.call("enqueue", path, status_code, JSON.stringify(value))


func _test_proxy_response_branches() -> void:
	var port := int(_server.get("port"))
	_clear_fixture()
	_enqueue_json("/api/v1/collections/peers", 200, [
		{"url": "http://annex.example:9000", "library_code": "Annex"},
	])
	var peers: Array = await _screen.call("_fetch_client_only_mdns_peers", port)
	_test.equal(peers.size(), 1, "Discovery accepts a valid proxy JSON array")
	_test.equal(peers[0].get("library_code", ""), "Annex", "Discovery preserves proxy peer data")

	_clear_fixture()
	_enqueue_json("/api/v1/collections/peers", 503, {"error": "unavailable"})
	_test.equal(await _screen.call("_fetch_client_only_mdns_peers", port), [], "Discovery ignores a non-200 proxy response")

	_clear_fixture()
	_server.call("enqueue", "/api/v1/collections/peers", 200, "not JSON")
	_test.equal(await _screen.call("_fetch_client_only_mdns_peers", port), [], "Discovery ignores malformed proxy JSON")

	_clear_fixture()
	_enqueue_json("/api/v1/collections/peers", 200, [
		{"url": "http://main.example:8888", "library_code": "Main"},
	])
	_test.equal((await _screen.call("_fetch_peers")).size(), 1, "Discovery accepts the server peer registry")

	_clear_fixture()
	_server.call("enqueue", "/api/v1/collections/peers", 200, "{")
	_test.equal(await _screen.call("_fetch_peers"), [], "Discovery ignores malformed server peer JSON")

	_clear_fixture()
	_enqueue_json("/api/v1/collections/peers", 404, {})
	_test.equal(await _screen.call("_fetch_peers"), [], "Discovery ignores a non-200 server peer response")


func _test_health_response_branches() -> void:
	for status_code in [200, 201, 204, 401, 403]:
		_clear_fixture()
		_server.call("enqueue", "/health", status_code, "")
		_test.expect(
			await _screen.call("_probe_url", "http://127.0.0.1:%d/health" % int(_server.get("port")), 1.0),
			"Discovery treats health status %d as a reachable endpoint" % status_code
		)
	for status_code in [404, 500, 503]:
		_clear_fixture()
		_server.call("enqueue", "/health", status_code, "")
		_test.expect(
			not await _screen.call("_probe_url", "http://127.0.0.1:%d/health" % int(_server.get("port")), 1.0),
			"Discovery rejects health status %d" % status_code
		)


func _test_auth_connection_branches() -> void:
	_settings.set("auth_username", "")
	_settings.set("auth_password", "")
	_settings.set("auth_scheme", "basic")
	_gs.base_url = ""
	_gs.library_name = ""
	_clear_fixture()
	_server.call("enqueue", "/api/v1/admin/settings", 401, "Unauthorized")
	await _screen.call(
		"_select_server",
		"http://127.0.0.1:%d/api/v1" % int(_server.get("port")),
		"Protected Library"
	)
	_test.expect(_screen.get_node("MainMargin/Root/AuthPanel").visible, "Discovery shows auth controls after a 401 response")
	_test.equal(_screen.get("_last_name"), "Protected Library", "Discovery remembers the library while waiting for auth")

	_clear_fixture()
	_enqueue_json("/api/v1/admin/settings", 200, {
		"catalog_medium_types": "Livre,BD",
		"catalog_levels": "CP,CE1",
	})
	_enqueue_json("/api/v1/admin/settings", 200, {
		"catalog_medium_types": "Livre,BD",
		"catalog_levels": "CP,CE1",
	})
	await _screen.call(
		"_select_server",
		"http://127.0.0.1:%d/api/v1" % int(_server.get("port")),
		"Connected Library"
	)
	await _test.wait_frames(self, 70)
	_test.equal(_gs.base_url, "http://127.0.0.1:%d/api/v1" % int(_server.get("port")), "Discovery keeps the connected API URL")
	_test.equal(_gs.library_name, "Connected Library", "Discovery stores the connected library name")
	_test.equal(_settings.get("last_library_name"), "Connected Library", "Discovery persists the connected library name")


func _test_peer_merging() -> void:
	var merged: Array = _screen.call("_merge_peers", [
		{"url": "http://library.example:8888/", "library_code": ""},
		{"url": "", "library_code": "Ignored"},
		"not a peer",
	], [
		{"url": "http://library.example:8888", "library_code": "Main Library"},
		{"url": "http://annex.example:9000/", "library_code": "Annex"},
	])
	_test.equal(merged.size(), 2, "Discovery removes duplicate and empty peer URLs")
	if merged.size() == 2:
		_test.equal(merged[0].get("url", ""), "http://library.example:8888", "Discovery normalizes duplicate peer URLs")
		_test.equal(merged[0].get("library_code", ""), "Main Library", "Discovery fills a missing duplicate library name")
	_test.equal(_screen.call("_merge_peers", [], []), [], "Discovery handles two empty peer lists")
