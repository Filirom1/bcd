extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const HTTP_SERVER = preload("res://tests/api_test_server.gd")
const API_HELPERS = preload("res://src/utils/ApiHelpers.gd")

var _test := SUPPORT.new()
var _server: Node
var _api: Node
var _gs: Node
var _settings: Node
var _previous_base_url := ""
var _previous_username := ""
var _previous_password := ""
var _previous_scheme := ""
var _previous_auth_origin := ""
var _previous_session_username := ""
var _previous_session_password := ""
var _previous_session_scheme := ""
var _previous_session_origin := ""


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	# Wait for autoloads and the scene tree before using the real transport.
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
	await _test_auth_scope_and_transport()
	await _test_digest_challenge_and_retry()
	await _test_concurrent_requests()
	_server.call("enqueue_delayed", "/api/v1/delayed", 200, '{"delayed":true}', 10)
	var delayed_result: Dictionary = await _request("GET", "/delayed")
	_test.equal(delayed_result, {"delayed": true}, "HTTP fixture releases delayed responses")
	await _test_network_result_code()
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
	_previous_auth_origin = str(_settings.get("auth_server_origin"))
	_previous_session_username = str(_settings.get("session_auth_username"))
	_previous_session_password = str(_settings.get("session_auth_password"))
	_previous_session_scheme = str(_settings.get("session_auth_scheme"))
	_previous_session_origin = str(_settings.get("session_auth_server_origin"))

func _restore_client_state() -> void:
	_gs.set("base_url", _previous_base_url)
	_settings.set("auth_username", _previous_username)
	_settings.set("auth_password", _previous_password)
	_settings.set("auth_scheme", _previous_scheme)
	_settings.set("auth_server_origin", _previous_auth_origin)
	_settings.call("set_session_auth", {
		"username": _previous_session_username,
		"password": _previous_session_password,
		"scheme": _previous_session_scheme,
		"server_origin": _previous_session_origin,
	})

func _set_auth(username: String, password: String, scheme: String) -> void:
	_settings.set("auth_username", username)
	_settings.set("auth_password", password)
	_settings.set("auth_scheme", scheme)
	_settings.call("set_session_auth", {
		"username": username,
		"password": password,
		"scheme": scheme,
		"server_origin": _settings.call("server_origin", str(_gs.get("base_url"))),
	})


func _test_response_matrix() -> void:
	_set_auth("", "", "basic")

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

	_server.call("enqueue", "/api/v1/borrowers", 200, "[]")
	var invalid_students: Dictionary = await _api.call("get_students", 1, "Al")
	_test.equal(
		invalid_students.get("detail", {}).get("code", ""),
		"invalid_response",
		"API rejects a student response with the wrong JSON shape"
	)

	_server.call("enqueue", "/api/v1/circulation/borrower/student/items", 200, '{"loans":null}')
	var invalid_loans: Dictionary = await _api.call("get_current_loans", "student")
	_test.equal(
		invalid_loans.get("detail", {}).get("code", ""),
		"invalid_response",
		"API rejects a loan response with a non-array loans field"
	)

	_server.call("enqueue", "/api/v1/circulation/checkout", 201, '{"transactions":{}}')
	var invalid_checkout: Dictionary = await _api.call("checkout", "student", ["A-1"])
	_test.equal(
		invalid_checkout.get("detail", {}).get("code", ""),
		"invalid_response",
		"API rejects a checkout response with a non-array transactions field"
	)

	_server.call("enqueue", "/api/v1/circulation/return", 200, '{"items":{}}')
	var invalid_return: Dictionary = await _api.call("return_items", ["A-1"])
	_test.equal(
		invalid_return.get("detail", {}).get("code", ""),
		"invalid_response",
		"API rejects a return response with a non-array items field"
	)

	_server.call("enqueue", "/api/v1/catalog/bibliographic/search", 200, '{"items":{}}')
	var invalid_search: Dictionary = await _api.call("search_catalog", "book", {})
	_test.equal(
		invalid_search.get("detail", {}).get("code", ""),
		"invalid_response",
		"API rejects a search response with a non-array items field"
	)


func _test_error_matrix() -> void:
	_set_auth("", "", "basic")

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
	_set_auth("alice", "secret", "basic")
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


func _test_auth_scope_and_transport() -> void:
	_set_auth("alice", "secret", "basic")
	var original_base := str(_gs.get("base_url"))
	_gs.set("base_url", "http://localhost:%d/api/v1" % int(_server.get("port")))
	_server.requests.clear()
	_server.call("enqueue", "/api/v1/auth/scoped", 200, '{"authenticated":true}')
	var scoped_result: Dictionary = await _request("GET", "/auth/scoped")
	_test.equal(scoped_result, {"authenticated": true}, "API reaches a different origin without reusing credentials")
	_test.equal(
		_server.call("last_request").get("headers", {}).get("authorization", ""),
		"",
		"API does not send credentials saved for another origin"
	)

	_settings.call("set_session_auth", {
		"username": "alice",
		"password": "secret",
		"scheme": "basic",
		"server_origin": "http://remote.example:8888",
	})
	_gs.set("base_url", original_base)
	_set_auth("", "", "basic")


func _test_digest_challenge_and_retry() -> void:
	_set_auth("alice", "secret", "digest")
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

	var challenge := 'Digest realm="BCD", nonce="sha-nonce", qop="auth-int", algorithm=SHA-256'
	var digest_auth := {
		"username": "alice",
		"password": "secret",
		"scheme": "digest",
		"server_origin": "http://127.0.0.1:%d" % int(_server.get("port")),
	}
	var digest_header: String = _api.call(
		"_build_digest_header", "POST", "/api/v1/digest", challenge,
		"{\"value\":1}", digest_auth, _gs.get("base_url")
	)
	var digest_nc := API_HELPERS.parse_digest_param(digest_header, "nc")
	var digest_cnonce := API_HELPERS.parse_digest_param(digest_header, "cnonce")
	var digest_ha1 := API_HELPERS.sha256("alice:BCD:secret")
	var digest_ha2 := API_HELPERS.sha256("POST:/api/v1/digest:" + API_HELPERS.sha256("{\"value\":1}"))
	var expected_response := API_HELPERS.sha256(
		"%s:%s:%s:%s:%s:%s" % [digest_ha1, "sha-nonce", digest_nc, digest_cnonce, "auth-int", digest_ha2]
	)
	_test.equal(API_HELPERS.parse_digest_param(digest_header, "algorithm"), "SHA-256", "Digest preserves the challenged algorithm")
	_test.equal(API_HELPERS.parse_digest_param(digest_header, "qop"), "auth-int", "Digest supports auth-int")
	_test.equal(API_HELPERS.parse_digest_param(digest_header, "response"), expected_response, "Digest computes the challenged SHA-256 auth-int response")
	_test.equal(
		_api.call("_build_digest_header", "GET", "/", 'Digest realm="BCD", nonce="n", algorithm=SHA-512', "", digest_auth, _gs.get("base_url")),
		"",
		"Digest rejects unsupported algorithms instead of sending a wrong response"
	)


func _test_concurrent_requests() -> void:
	_set_auth("", "", "basic")
	_server.requests.clear()
	_server.call("enqueue", "/api/v1/concurrent/one", 200, '{"value":1}')
	_server.call("enqueue", "/api/v1/concurrent/two", 200, '{"value":2}')

	var first = _api.call("_request", "GET", "/concurrent/one")
	var second = _api.call("_request", "GET", "/concurrent/two")
	var first_result = await first
	var second_result = await second
	_test.equal(first_result, {"value": 1.0}, "API completes the first concurrent request")
	_test.equal(second_result, {"value": 2.0}, "API completes the second concurrent request")
	_test.equal(_server.requests.size(), 2, "API does not reject a concurrent request as busy")


func _test_network_result_code() -> void:
	var previous_base_url := str(_gs.get("base_url"))
	_set_auth("", "", "basic")
	_gs.set("base_url", "http://127.0.0.1:1/api/v1")
	var result: Dictionary = await _request("GET", "/unreachable")
	_test.equal(
		result,
		{"error": true, "detail": {"code": "network_error", "details": {}}},
		"API maps a failed transport result to network_error"
	)
	_gs.set("base_url", previous_base_url)


func _test_methods_and_request_bodies() -> void:
	_set_auth("", "", "basic")
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
