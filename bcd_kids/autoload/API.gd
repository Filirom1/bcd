# Autoload "API" - HTTP Service
extends Node

const API_HELPERS = preload("res://src/utils/ApiHelpers.gd")
const API_RESULT = preload("res://src/utils/ApiResult.gd")
const DATA = preload("res://src/utils/DataHelper.gd")
const POPULAR_BOOKS_CACHE = preload("res://src/utils/PopularBooksCache.gd")

# Number of requests currently waiting for HTTP completion. This is exposed for
# deterministic workflow tests and avoids coupling them to a specific node.
var in_flight_requests := 0
var _debug_logging := false
var _digest_challenges: Dictionary = {}
var _digest_nonce_counts: Dictionary = {}

func _ready() -> void:
	_debug_logging = OS.get_environment("BCD_GODOT_DEBUG").to_lower() in ["1", "true", "yes"]
	# HTTPRequest nodes are created per call in _send_request(). This prevents one
	# slow request from returning ERR_BUSY to unrelated screens.
	# Settings are loaded after a server has been confirmed.

# ============================================================================
# Settings
# ============================================================================

func load_settings() -> Dictionary:
	_debug("Loading settings")
	var settings = await get_settings()
	if settings is Dictionary and not settings.has("error"):
		apply_settings(settings)
		return settings
	_debug("Settings response was not a successful object")
	return settings if settings is Dictionary else _invalid_response("object")

func load_settings_for_server(base_url: String, auth: Dictionary = {}) -> Dictionary:
	return await get_settings_for_server(base_url, auth)

func apply_settings(settings: Dictionary) -> void:
	GS.settings = settings
	GS.filter_medium_types = GS.parse_csv_list(DATA.text(settings, "catalog_medium_types"))
	_debug("Settings loaded successfully")

func get_settings():
	return _expect_dictionary(await _request("GET", "/admin/settings"))

func get_settings_for_server(base_url: String, auth: Dictionary = {}):
	var api_base := base_url.rstrip("/")
	if not api_base.ends_with("/api/v1"):
		api_base += "/api/v1"
	return _expect_dictionary(await _request("GET", "/admin/settings", null, api_base, auth))

func get_most_borrowed_titles(period: String = "year", limit: int = 5):
	var safe_period := period if period in ["week", "month", "year", "all", "all-time"] else "year"
	var safe_limit := clampi(limit, 1, POPULAR_BOOKS_CACHE.CACHE_LIMIT)
	var query := "?period=%s&limit=%d" % [safe_period.uri_encode(), safe_limit]
	return _expect_dictionary(await _request("GET", "/reports/most-borrowed" + query))

func refresh_popular_books() -> Array[String]:
	# This runs on the API autoload so the refresh can finish even when the
	# discovery screen is replaced immediately after a successful connection.
	var result = await get_most_borrowed_titles("month", POPULAR_BOOKS_CACHE.CACHE_LIMIT)
	if not (result is Dictionary) or result.has("error"):
		return []
	var books := POPULAR_BOOKS_CACHE.normalize(result.get("titles", []))
	if books.is_empty():
		return []
	return books if POPULAR_BOOKS_CACHE.save_books(books) else []

# ============================================================================
# Classes
# ============================================================================

func get_classes():
	_debug("get_classes")
	var result = await _request("GET", "/classes")
	_debug("get_classes result type: %s" % str(typeof(result)))

	if result is Dictionary and result.has("error"):
		_debug("get_classes returned an error")
		return result

	if result is Array:
		_debug("get_classes returned an array")
		return result

	_debug("get_classes returned an unexpected type: %s" % str(typeof(result)))
	return _invalid_response("array")

# ============================================================================
# Borrowers
# ============================================================================

func get_students(class_id: int, search: String = ""):
	var query = "?class_id=%d&role=student&limit=500" % class_id
	if search:
		query += "&q=" + search.uri_encode()
	return _expect_dictionary_array(await _request("GET", "/borrowers" + query), "items")

func get_borrower(borrower_id: String):
	return _expect_dictionary(await _request("GET", "/borrowers/" + borrower_id.uri_encode()))

# ============================================================================
# Circulation
# ============================================================================

func get_current_loans(borrower_id: String):
	return _expect_dictionary_array(
		await _request("GET", "/circulation/borrower/" + borrower_id.uri_encode() + "/items"),
		"loans"
	)

func renew_items(borrower_id: String, item_ids: Array = []):
	var body: Dictionary = {"borrower_id": borrower_id}
	if not item_ids.is_empty():
		body["item_ids"] = item_ids
	return _expect_dictionary_array(await _request("POST", "/circulation/renew", body), "renewed")

func get_bibliographic_record(biblio_id: int):
	return _expect_dictionary(await _request("GET", "/catalog/bibliographic/" + str(biblio_id)))

func get_cover_url(cover_filename: String) -> String:
	var base := GS.base_url.rstrip("/")
	if base.is_empty() or cover_filename.is_empty():
		return ""
	if "/api/v1" in base:
		base = base.split("/api/v1")[0]
	return base + "/covers/" + cover_filename.uri_encode()

func checkout(borrower_id: String, item_ids: Array):
	var body = {
		"borrower_id": borrower_id,
		"item_ids": item_ids,
		"checked_out_by": "godot-ui"
	}
	return _expect_dictionary_array(await _request("POST", "/circulation/checkout", body), "transactions")

func return_items(item_ids: Array):
	var body = {
		"item_ids": item_ids,
		"returned_by": "godot-ui"
	}
	return _expect_dictionary_array(await _request("POST", "/circulation/return", body), "items")

# ============================================================================
# Catalog Search
# ============================================================================

func search_catalog(query: String, filters: Dictionary):
	var params := []

	if query:
		params.append("q=" + query.uri_encode())

	if filters.get("medium_type"):
		params.append("medium_type=" + filters.medium_type.uri_encode())

	if filters.get("target_audience"):
		params.append("target_audience=" + str(filters.target_audience).uri_encode())

	if filters.get("available_only"):
		params.append("available_only=true")

	params.append("limit=50")

	var query_string = "?" + "&".join(params) if params.size() > 0 else ""
	return _expect_dictionary_array(
		await _request("GET", "/catalog/bibliographic/search" + query_string),
		"items"
	)

# ============================================================================
# Holds
# ============================================================================

func get_holds(borrower_db_id: int):
	var result = await _request("GET", "/holds/borrower/" + str(borrower_db_id))
	if result is Dictionary and result.has("error"):
		return result
	return result if result is Array else _invalid_response("array")

func create_hold(borrower_db_id: int, biblio_record_id: int):
	var body = {
		"borrower_id": borrower_db_id,
		"bibliographic_record_id": biblio_record_id,
		"created_by": "godot-ui",
		"notes": ""
	}
	return _expect_dictionary(await _request("POST", "/holds", body))

func cancel_hold(hold_id: int):
	return _expect_dictionary(await _request("DELETE", "/holds/" + str(hold_id)))

# ============================================================================
# Helpers
# ============================================================================

func to_result(value: Variant) -> ApiResult:
	# New callers can opt into a typed envelope while existing screens keep the
	# legacy Dictionary/Array contract during the API migration.
	return API_RESULT.from_legacy(value)

func _invalid_response(expected: String) -> Dictionary:
	return {
		"error": true,
		"detail": {"code": "invalid_response", "details": {"expected": expected}},
	}

func _expect_dictionary(result, expected: String = "object") -> Dictionary:
	if result is Dictionary:
		return result
	return _invalid_response(expected)

func _expect_dictionary_array(result, key: String) -> Dictionary:
	if not (result is Dictionary):
		return _invalid_response("object with array field: " + key)
	if result.has("error"):
		return result
	if result.get(key) is Array:
		return result
	return _invalid_response("object with array field: " + key)

func _extract_uri(url: String) -> String:
	return API_HELPERS.extract_uri(url)

func _find_header(headers: PackedStringArray, name: String) -> String:
	var prefix = name.to_lower() + ":"
	for h in headers:
		if h.to_lower().begins_with(prefix):
			return h.substr(prefix.length()).strip_edges()
	return ""

func _parse_digest_param(header: String, param: String) -> String:
	return API_HELPERS.parse_digest_param(header, param)

func _md5(text: String) -> String:
	return API_HELPERS.md5(text)

func _hash_digest(text: String, algorithm: String) -> String:
	match algorithm.to_lower():
		"md5":
			return API_HELPERS.md5(text)
		"sha-256":
			return API_HELPERS.sha256(text)
		_:
			return ""

func _build_digest_header(
		method: String,
		uri: String,
		www_auth: String,
		body: String = "",
		auth: Dictionary = {},
		server_url: String = ""
) -> String:
	var username := str(auth.get("username", Settings.auth_username))
	var password := str(auth.get("password", Settings.auth_password))
	var realm := _parse_digest_param(www_auth, "realm")
	var nonce := _parse_digest_param(www_auth, "nonce")
	var opaque := _parse_digest_param(www_auth, "opaque")
	var algorithm := _parse_digest_param(www_auth, "algorithm")
	if algorithm.is_empty():
		algorithm = "MD5"
	var normalized_algorithm := algorithm.to_lower()
	var base_algorithm := normalized_algorithm.replace("-sess", "")
	if base_algorithm not in ["md5", "sha-256"]:
		return ""
	var is_session_algorithm := normalized_algorithm.ends_with("-sess")

	var qop_header := _parse_digest_param(www_auth, "qop")
	var qop := ""
	for qop_value in qop_header.to_lower().split(","):
		var candidate := qop_value.strip_edges()
		if candidate == "auth":
			qop = "auth"
			break
		if candidate == "auth-int":
			qop = "auth-int"
	if not qop_header.is_empty() and qop.is_empty():
		return ""

	var hash_prefix := _hash_digest("%s:%s:%s" % [username, realm, password], base_algorithm)
	if hash_prefix.is_empty():
		return ""
	var origin := Settings.server_origin(server_url)
	var state_key := "%s|%s|%s|%s" % [origin, realm, base_algorithm, qop]
	var previous_nonce := str(_digest_challenges.get(origin, {}).get("nonce", ""))
	if previous_nonce != nonce:
		_digest_nonce_counts[state_key] = 0
	_digest_challenges[origin] = {"header": www_auth, "nonce": nonce}

	var nc_value := int(_digest_nonce_counts.get(state_key, 0)) + 1
	_digest_nonce_counts[state_key] = nc_value
	var nc := "%08x" % nc_value
	var cnonce := _md5("%s:%s:%s" % [Time.get_ticks_usec(), nonce, username])
	var ha1 := hash_prefix
	if is_session_algorithm:
		ha1 = _hash_digest("%s:%s:%s" % [hash_prefix, nonce, cnonce], base_algorithm)

	var ha2_input := "%s:%s" % [method, uri]
	if qop == "auth-int":
		ha2_input += ":" + _hash_digest(body, base_algorithm)
	var ha2 := _hash_digest(ha2_input, base_algorithm)
	var response_input: String
	if qop.is_empty():
		response_input = "%s:%s:%s" % [ha1, nonce, ha2]
	else:
		response_input = "%s:%s:%s:%s:%s:%s" % [ha1, nonce, nc, cnonce, qop, ha2]
	var response := _hash_digest(response_input, base_algorithm)
	if response.is_empty():
		return ""

	var header := 'Digest username="%s", realm="%s", nonce="%s", uri="%s", algorithm=%s' \
			% [username, realm, nonce, uri, algorithm]
	if not qop.is_empty():
		header += ', qop=%s, nc=%s, cnonce="%s"' % [qop, nc, cnonce]
	header += ', response="%s"' % response
	if not opaque.is_empty():
		header += ', opaque="%s"' % opaque
	return header

# ============================================================================
# Generic HTTP Request
# ============================================================================

func _network_error() -> Dictionary:
	return {"error": true, "detail": {"code": "network_error", "details": {}}}

func _unknown_error() -> Dictionary:
	return {"error": true, "detail": {"code": "unknown_error", "details": {}}}

func _send_request(
		url: String,
		headers: PackedStringArray,
		http_method: int,
		body_string: String
) -> Array:
	# HTTPRequest is single-use while a request is active. A private node per
	# call allows independent screens to load data concurrently without ERR_BUSY.
	var request := HTTPRequest.new()
	request.timeout = 10.0
	add_child(request)
	in_flight_requests += 1

	var request_error := request.request(url, headers, http_method, body_string)
	if request_error != OK:
		in_flight_requests -= 1
		request.queue_free()
		push_error("[API] HTTP request failed: " + str(request_error))
		return [HTTPRequest.RESULT_CANT_CONNECT, 0, PackedStringArray(), PackedByteArray()]

	var response: Array = await request.request_completed
	in_flight_requests -= 1
	request.queue_free()
	return response

func _request(
		method: String,
		endpoint: String,
		body = null,
		base_url_override: String = "",
		auth_override: Dictionary = {}
):
	# A request cannot be meaningful until a server has been selected. Returning
	# the same structured network error used by HTTPRequest keeps startup and
	# headless tests deterministic instead of asking HTTPRequest to parse a
	# relative URL such as "/classes".
	var base_url := base_url_override.rstrip("/") if not base_url_override.is_empty() else str(GS.base_url).rstrip("/")
	if base_url.is_empty():
		return _network_error()

	var url := base_url + endpoint
	var headers := PackedStringArray(["Content-Type: application/json"])
	var body_string := JSON.stringify(body) if body != null else ""
	var auth := _resolve_auth(base_url, auth_override)
	var origin := Settings.server_origin(base_url)

	var auth_scheme := str(auth.get("scheme", "basic")).to_lower()
	if auth_scheme == "basic" and not auth.is_empty():
		var creds := str(auth.get("username", "")) + ":" + str(auth.get("password", ""))
		headers.append("Authorization: Basic " + Marshalls.utf8_to_base64(creds))
		_debug("Basic authentication configured for the selected server")
	elif auth_scheme == "digest" and not auth.is_empty():
		var cached_challenge: Dictionary = _digest_challenges.get(origin, {})
		var cached_header := str(cached_challenge.get("header", ""))
		if not cached_header.is_empty():
			var cached_digest := _build_digest_header(
				method, _extract_uri(url), cached_header, body_string, auth, base_url)
			if cached_digest.is_empty():
				return _auth_error("unsupported_digest")
			headers.append("Authorization: " + cached_digest)

	_debug("%s %s" % [method, url])

	var http_method := HTTPClient.METHOD_GET
	match method:
		"GET": http_method = HTTPClient.METHOD_GET
		"POST": http_method = HTTPClient.METHOD_POST
		"PUT": http_method = HTTPClient.METHOD_PUT
		"DELETE": http_method = HTTPClient.METHOD_DELETE

	var response: Array = await _send_request(url, headers, http_method, body_string)
	if response[0] != HTTPRequest.RESULT_SUCCESS:
		return _network_error()

	var status_code: int = response[1]
	var resp_headers: PackedStringArray = response[2]
	var response_body: PackedByteArray = response[3]

	# Digest authentication uses the server challenge once and then reuses its
	# nonce with an incremented nonce-count for subsequent requests.
	if status_code == 401 and auth_scheme == "digest" and not auth.is_empty():
		var www_auth := _find_header(resp_headers, "www-authenticate")
		if www_auth.to_lower().begins_with("digest"):
			_digest_challenges[origin] = {
				"header": www_auth,
				"nonce": _parse_digest_param(www_auth, "nonce"),
			}
			var digest := _build_digest_header(
				method, _extract_uri(url), www_auth, body_string, auth, base_url)
			if digest.is_empty():
				return _auth_error("unsupported_digest")
			var auth_headers: PackedStringArray = headers.duplicate()
			# Replace a preemptive Authorization header if the cached challenge was stale.
			var replaced_authorization := false
			for index in range(auth_headers.size() - 1, -1, -1):
				if auth_headers[index].to_lower().begins_with("authorization:"):
					auth_headers.remove_at(index)
					replaced_authorization = true
					break
			if replaced_authorization or not auth_headers.has("Authorization: " + digest):
				auth_headers.append("Authorization: " + digest)
			response = await _send_request(url, auth_headers, http_method, body_string)
			if response[0] != HTTPRequest.RESULT_SUCCESS:
				return _network_error()
			status_code = response[1]
			resp_headers = response[2]
			response_body = response[3]
			if status_code == 401:
				_digest_challenges.erase(origin)
				return _auth_error("auth_required")

	_debug("Response status: %d" % status_code)

	if status_code < 200 or status_code >= 300:
		if status_code == 401:
			return _auth_error("auth_required")

		var error_text := response_body.get_string_from_utf8()
		var error_json := JSON.new()
		var parse_error = error_json.parse(error_text)

		# Parse BCD API error format:
		# {"success": false, "error": "...", "error_code": "...", "context": {...}}
		if parse_error == OK and error_json.data is Dictionary:
			var error_data: Dictionary = error_json.data
			if error_data.has("error_code"):
				var code := str(error_data.error_code).to_lower()
				var context = error_data.get("context", {})
				return {"error": true, "detail": {"code": code, "details": context}}
			if error_data.has("details") and error_data.details is Array:
				return {"error": true, "detail": {"code": "validation_error", "details": {}}}

		return _unknown_error()

	var text := response_body.get_string_from_utf8()
	if text.is_empty():
		_debug("Empty response body")
		return {}

	var response_json := JSON.new()
	var response_parse_error = response_json.parse(text)
	if response_parse_error != OK:
		push_error("[API] JSON parse error: " + response_json.get_error_message())
		return {"error": true, "detail": {"code": "parse_error", "details": {}}}

	var data_type := "null"
	if response_json.data is Array:
		data_type = "Array[%d]" % response_json.data.size()
	elif response_json.data is Dictionary:
		data_type = "Dictionary with keys: %s" % str(response_json.data.keys())
	elif response_json.data != null:
		data_type = str(typeof(response_json.data))

	_debug("Parsed data type: " + data_type)
	return response_json.data if response_json.data != null else {}

func _auth_error(code: String) -> Dictionary:
	return {"error": true, "detail": {"code": code, "details": {}}}

func _resolve_auth(base_url: String, override: Dictionary) -> Dictionary:
	if not override.is_empty() and not str(override.get("username", "")).is_empty():
		return override.duplicate(true)
	var session := Settings.get_session_auth_for_server(base_url)
	if not session.is_empty():
		return session
	return Settings.get_saved_auth_for_server(base_url)

func _debug(message: String) -> void:
	if _debug_logging:
		print("[API] " + message)
