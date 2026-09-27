extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const HTTP_SERVER = preload("res://tests/api_test_server.gd")

var _test := SUPPORT.new()
var _server: Node
var _api: Node
var _gs: Node
var _settings: Node
var _previous_base_url := ""
var _previous_username := ""
var _previous_password := ""
var _previous_scheme := ""


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	# API._ready() creates its HTTPRequest asynchronously, so wait before using
	# the real transport rather than replacing it with a mock.
	await _test.wait_frames(self, 3)
	_api = get_root().get_node("API")
	_gs = get_root().get_node("GS")
	_settings = get_root().get_node("Settings")
	_save_client_state()

	_server = HTTP_SERVER.new()
	get_root().add_child(_server)
	if not _server.call("start"):
		_test.expect(false, "HTTP fixture starts on an ephemeral loopback port")
		_restore_client_state()
		_test.finish(self)
		return
	await _test.wait_frames(self)
	_gs.base_url = "http://127.0.0.1:%d/api/v1" % int(_server.get("port"))

	await _test_response_matrix()
	await _test_error_matrix()
	await _test_basic_auth()
	await _test_digest_challenge_and_retry()
	await _test_methods_and_request_bodies()

	_restore_client_state()
	_server.call("stop")
	_server.queue_free()
	await _test.wait_frames(self, 2)
	_test.finish(self)


func _save_client_state() -> void:
	_previous_base_url = str(_gs.get("base_url"))
	_previous_username = str(_settings.get("auth_username"))
	_previous_password = str(_settings.get("auth_password"))
	_previous_scheme = str(_settings.get("auth_scheme"))


func _restore_client_state() -> void:
	_gs.set("base_url", _previous_base_url)
	_settings.set("auth_username", _previous_username)
	_settings.set("auth_password", _previous_password)
	_settings.set("auth_scheme", _previous_scheme)


func _test_response_matrix() -> void:
	_settings.set("auth_username", "")
	_settings.set("auth_password", "")
	_settings.set("auth_scheme", "basic")

	_server.call("enqueue", "/api/v1/matrix/object", 200, '{"ok":true,"count":2}')
	var object_result = await _request("GET", "/matrix/object")
	_test.equal(object_result, {"ok": true, "count": 2.0}, "API parses a successful JSON object")

	_server.call("enqueue", "/api/v1/matrix/array", 200, '[{"id":1},{"id":2}]')
	var array_result = await _request("GET", "/matrix/array")
	_test.equal(array_result, [{"id": 1.0}, {"id": 2.0}], "API parses a successful JSON array")

	_server.call("enqueue", "/api/v1/matrix/scalar", 200, '"ready"')
	var scalar_result = await _request("GET", "/matrix/scalar")
	_test.equal(scalar_result, "ready", "API returns a successful scalar JSON value")

	_server.call("enqueue", "/api/v1/matrix/boolean", 200, "false")
	var boolean_result = await _request("GET", "/matrix/boolean")
	_test.equal(boolean_result, false, "API preserves a false scalar JSON value")

	_server.call("enqueue", "/api/v1/matrix/number", 200, "42")
	var number_result = await _request("GET", "/matrix/number")
	_test.equal(number_result, 42.0, "API returns a successful numeric scalar JSON value")

	_server.call("enqueue", "/api/v1/matrix/empty", 204, "")
	var empty_result = await _request("GET", "/matrix/empty")
	_test.equal(empty_result, {}, "API maps a successful empty body to an empty Dictionary")

	_server.call("enqueue", "/api/v1/matrix/malformed", 200, "{not valid json")
	var malformed_result: Dictionary = await _request("GET", "/matrix/malformed")
	_test.equal(
		malformed_result,
		{"error": true, "detail": {"code": "parse_error", "details": {}}},
		"API returns a parse error for malformed successful JSON"
	)


func _test_error_matrix() -> void:
	_settings.set("auth_username", "")
	_settings.set("auth_password", "")
	_settings.set("auth_scheme", "basic")

	_server.call("enqueue", "/api/v1/errors/401", 401, "Unauthorized")
	var unauthorized: Dictionary = await _request("GET", "/errors/401")
	_test.equal(
		unauthorized.get("detail", {}).get("code", ""),
		"auth_required",
		"API maps HTTP 401 to auth_required"
	)

	_server.call("enqueue", "/api/v1/errors/404", 404, "Not found")
	var not_found: Dictionary = await _request("GET", "/errors/404")
	_test.equal(
		not_found,
		{"error": true, "detail": {"code": "unknown_error", "details": {}}},
		"API maps an unstructured HTTP 404 to unknown_error"
	)

	_server.call(
		"enqueue",
		"/api/v1/errors/422",
		422,
		'{"success":false,"error":"Validation error","details":[{"loc":["body","title"],"msg":"required"}]}'
	)
	var validation: Dictionary = await _request("GET", "/errors/422")
	_test.equal(
		validation,
		{"error": true, "detail": {"code": "validation_error", "details": {}}},
		"API recognizes the BCD validation error envelope"
	)

	_server.call("enqueue", "/api/v1/errors/500", 500, '{"error":"database unavailable"}')
	var server_error: Dictionary = await _request("GET", "/errors/500")
	_test.equal(
		server_error.get("detail", {}).get("code", ""),
		"unknown_error",
		"API hides technical details from an HTTP 500"
	)

	_server.call(
		"enqueue",
		"/api/v1/errors/bcd",
		404,
		'{"success":false,"error":"Item A-1 was not found","error_code":"ITEM_NOT_FOUND","context":{"item_id":"A-1","status":"missing"}}'
	)
	var bcd_error: Dictionary = await _request("GET", "/errors/bcd")
	_test.equal(
		bcd_error,
		{
			"error": true,
			"detail": {
				"code": "item_not_found",
				"details": {"item_id": "A-1", "status": "missing"},
			},
		},
		"API preserves a BCD error code and context"
	)


func _test_basic_auth() -> void:
	_settings.set("auth_username", "alice")
	_settings.set("auth_password", "secret")
	_settings.set("auth_scheme", "basic")
	_server.requests.clear()
	_server.call("enqueue", "/api/v1/auth/basic", 200, '{"authenticated":true}')

	var result: Dictionary = await _request("GET", "/auth/basic")
	_test.equal(result, {"authenticated": true}, "API accepts a Basic-authenticated response")
	var request: Dictionary = _server.call("last_request")
	var headers: Dictionary = request.get("headers", {})
	_test.equal(
		headers.get("authorization", ""),
		"Basic YWxpY2U6c2VjcmV0",
		"API generates the expected Basic Authorization header"
	)


func _test_digest_challenge_and_retry() -> void:
	_settings.set("auth_username", "alice")
	_settings.set("auth_password", "secret")
	_settings.set("auth_scheme", "digest")
	_server.requests.clear()
	_server.call(
		"enqueue",
		"/api/v1/auth/digest",
		401,
		"Unauthorized",
		{"WWW-Authenticate": 'Digest realm="BCD", nonce="nonce-123", qop="auth", opaque="opaque-value"'}
	)
	_server.call("enqueue", "/api/v1/auth/digest", 200, '{"authenticated":true}')

	var result: Dictionary = await _request("GET", "/auth/digest")
	_test.equal(result, {"authenticated": true}, "API retries a Digest challenge successfully")
	_test.equal(_server.requests.size(), 2, "Digest authentication sends an initial request and one retry")
	if _server.requests.size() >= 2:
		var first_headers: Dictionary = _server.requests[0].get("headers", {})
		var retry_headers: Dictionary = _server.requests[1].get("headers", {})
		_test.equal(first_headers.get("authorization", ""), "", "Digest starts without an Authorization header")
		var authorization: String = retry_headers.get("authorization", "")
		_test.expect(authorization.begins_with("Digest username=\"alice\""), "Digest retry includes the username")
		_test.expect(authorization.contains('uri="/api/v1/auth/digest"'), "Digest retry uses the request URI")
		_test.expect(authorization.contains("qop=auth"), "Digest retry includes the challenged qop")
		_test.expect(authorization.contains('opaque="opaque-value"'), "Digest retry preserves the opaque challenge value")


func _test_methods_and_request_bodies() -> void:
	_settings.set("auth_username", "")
	_settings.set("auth_password", "")
	_settings.set("auth_scheme", "basic")
	_server.requests.clear()
	for _method in ["GET", "POST", "PUT", "DELETE"]:
		_server.call("enqueue", "/api/v1/methods", 200, '{"accepted":true}')

	var get_result = await _request("GET", "/methods")
	var post_result = await _request("POST", "/methods", {"name": "Alice", "ids": [1, 2]})
	var put_result = await _request("PUT", "/methods", {"enabled": true})
	var delete_result = await _request("DELETE", "/methods", {"id": 7})
	_test.expect(get_result.get("accepted", false), "API sends GET requests")
	_test.expect(post_result.get("accepted", false), "API sends POST requests")
	_test.expect(put_result.get("accepted", false), "API sends PUT requests")
	_test.expect(delete_result.get("accepted", false), "API sends DELETE requests")
	_test.equal(_server.requests.size(), 4, "API sends one request for each supported HTTP method")

	if _server.requests.size() == 4:
		_test.equal(_server.requests[0].get("method", ""), "GET", "API maps GET to HTTP GET")
		_test.equal(_server.requests[0].get("body", ""), "", "API leaves a null GET body empty")
		_test.equal(_server.requests[1].get("method", ""), "POST", "API maps POST to HTTP POST")
		_test.equal(
			JSON.parse_string(_server.requests[1].get("body", "")),
			{"name": "Alice", "ids": [1.0, 2.0]},
			"API JSON-encodes a POST request body"
		)
		_test.equal(_server.requests[2].get("method", ""), "PUT", "API maps PUT to HTTP PUT")
		_test.equal(
			JSON.parse_string(_server.requests[2].get("body", "")),
			{"enabled": true},
			"API JSON-encodes a PUT request body"
		)
		_test.equal(_server.requests[3].get("method", ""), "DELETE", "API maps DELETE to HTTP DELETE")
		_test.equal(
			JSON.parse_string(_server.requests[3].get("body", "")),
			{"id": 7.0},
			"API JSON-encodes a DELETE request body when supplied"
		)


func _request(method: String, endpoint: String, body = null):
	if body == null:
		return await _api.call("_request", method, endpoint)
	return await _api.call("_request", method, endpoint, body)
