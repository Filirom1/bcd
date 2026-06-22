# Autoload "API" - HTTP Service
extends Node

var http: HTTPRequest

func _ready():
	http = HTTPRequest.new()
	http.timeout = 10.0
	add_child(http)
	# Wait for HTTP to be ready
	await get_tree().process_frame
	await get_tree().process_frame
	# Don't auto-load settings - they will be loaded after server selection

# ============================================================================
# Settings
# ============================================================================

func load_settings() -> void:
	print("[API] Loading settings...")
	var settings = await get_settings()
	print("[API] Settings result type: %s" % str(typeof(settings)))

	if settings is Dictionary:
		if settings.has("error"):
			print("[API] Settings error: %s" % settings.get("message", "Unknown"))
		else:
			print("[API] Settings loaded successfully, keys: %s" % str(settings.keys()))
			GS.settings = settings
			GS.filter_medium_types = GS.parse_csv_list(settings.get("catalog_medium_types", ""))
			GS.filter_levels = GS.parse_csv_list(settings.get("catalog_levels", ""))
	else:
		print("[API] Settings is not a Dictionary! Type: %s" % str(typeof(settings)))

func get_settings():
	return await _request("GET", "/admin/settings")

# ============================================================================
# Classes
# ============================================================================

func get_classes() -> Array:
	print("[API] get_classes() called")
	var result = await _request("GET", "/classes")
	print("[API] get_classes() result type: %s" % str(typeof(result)))

	if result is Dictionary and result.has("error"):
		print("[API] get_classes() error: %s" % result.get("message", "Unknown"))
		return []

	if result is Array:
		print("[API] get_classes() returning Array with %d items" % result.size())
		return result
	else:
		print("[API] get_classes() result is not an Array! Type: %s" % str(typeof(result)))
		return []

# ============================================================================
# Borrowers
# ============================================================================

func get_students(class_id: int, search: String = ""):
	var query = "?class_id=%d&role=student&limit=500" % class_id
	if search:
		query += "&q=" + search.uri_encode()
	return await _request("GET", "/borrowers" + query)

func get_borrower(borrower_id: String):
	return await _request("GET", "/borrowers/" + borrower_id)

# ============================================================================
# Circulation
# ============================================================================

func get_current_loans(borrower_id: String):
	return await _request("GET", "/circulation/borrower/" + borrower_id + "/items")

func renew_items(borrower_id: String, item_ids: Array = []):
	var body: Dictionary = {"borrower_id": borrower_id}
	if not item_ids.is_empty():
		body["item_ids"] = item_ids
	return await _request("POST", "/circulation/renew", body)

func get_bibliographic_record(biblio_id: int):
	return await _request("GET", "/catalog/bibliographic/" + str(biblio_id))

func get_cover_url(cover_filename: String) -> String:
	var base := GS.base_url.rstrip("/")
	if "/api/v1" in base:
		base = base.split("/api/v1")[0]
	return base + "/covers/" + cover_filename

func checkout(borrower_id: String, item_ids: Array):
	var body = {
		"borrower_id": borrower_id,
		"item_ids": item_ids,
		"checked_out_by": "godot-ui"
	}
	return await _request("POST", "/circulation/checkout", body)

func return_items(item_ids: Array):
	var body = {
		"item_ids": item_ids,
		"returned_by": "godot-ui"
	}
	return await _request("POST", "/circulation/return", body)

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
		params.append("target_audience=" + filters.target_audience)

	if filters.get("available_only"):
		params.append("available_only=true")

	params.append("limit=50")

	var query_string = "?" + "&".join(params) if params.size() > 0 else ""
	return await _request("GET", "/catalog/bibliographic/search" + query_string)

# ============================================================================
# Holds
# ============================================================================

func get_holds(borrower_db_id: int) -> Array:
	var result = await _request("GET", "/holds/borrower/" + str(borrower_db_id))
	if result is Dictionary and result.has("error"):
		return []
	return result if result is Array else []

func create_hold(borrower_db_id: int, biblio_record_id: int):
	var body = {
		"borrower_id": borrower_db_id,
		"bibliographic_record_id": biblio_record_id,
		"created_by": "godot-ui",
		"notes": ""
	}
	return await _request("POST", "/holds", body)

func cancel_hold(hold_id: int) -> void:
	await _request("DELETE", "/holds/" + str(hold_id))

# ============================================================================
# Helpers
# ============================================================================

func _extract_uri(url: String) -> String:
	var parts = url.split("://", false, 1)
	if parts.size() < 2: return "/"
	var slash = parts[1].find("/")
	return parts[1].substr(slash) if slash != -1 else "/"

func _find_header(headers: PackedStringArray, name: String) -> String:
	var prefix = name.to_lower() + ":"
	for h in headers:
		if h.to_lower().begins_with(prefix):
			return h.substr(prefix.length()).strip_edges()
	return ""

func _parse_digest_param(header: String, param: String) -> String:
	var idx = header.to_lower().find((param + "=").to_lower())
	if idx == -1: return ""
	var start = idx + param.length() + 1
	if start >= header.length(): return ""
	if header[start] == '"':
		start += 1
		var e = header.find('"', start)
		return header.substr(start, e - start) if e != -1 else ""
	var e = header.find(",", start)
	return header.substr(start, (e if e != -1 else header.length()) - start).strip_edges()

func _md5(text: String) -> String:
	var ctx := HashingContext.new()
	ctx.start(HashingContext.HASH_MD5)
	ctx.update(text.to_utf8_buffer())
	return ctx.finish().hex_encode()

func _build_digest_header(method: String, uri: String, www_auth: String) -> String:
	var realm  = _parse_digest_param(www_auth, "realm")
	var nonce  = _parse_digest_param(www_auth, "nonce")
	var opaque = _parse_digest_param(www_auth, "opaque")
	var alg    = _parse_digest_param(www_auth, "algorithm")
	if alg.is_empty(): alg = "MD5"
	var qop    = _parse_digest_param(www_auth, "qop").split(",")[0].strip_edges()

	var ha1 = _md5("%s:%s:%s" % [Settings.auth_username, realm, Settings.auth_password])
	var ha2 = _md5("%s:%s"   % [method, uri])

	var header = 'Digest username="%s", realm="%s", nonce="%s", uri="%s", algorithm=%s' \
				 % [Settings.auth_username, realm, nonce, uri, alg]

	if qop == "auth" or qop == "auth-int":
		var nc       = "00000001"
		var cnonce   = _md5(str(Time.get_unix_time_from_system()))
		var response = _md5("%s:%s:%s:%s:%s:%s" % [ha1, nonce, nc, cnonce, "auth", ha2])
		header += ', qop=auth, nc=%s, cnonce="%s", response="%s"' % [nc, cnonce, response]
	else:
		header += ', response="%s"' % _md5("%s:%s:%s" % [ha1, nonce, ha2])

	# Add opaque if server provided it (required by some implementations)
	if not opaque.is_empty():
		header += ', opaque="%s"' % opaque

	return header

# ============================================================================
# Generic HTTP Request
# ============================================================================

func _request(method: String, endpoint: String, body = null):
	var url = GS.base_url + endpoint
	var headers = ["Content-Type: application/json"]

	# Add authentication header if credentials are set
	if not Settings.auth_username.is_empty() and Settings.auth_scheme == "basic":
		var creds = Settings.auth_username + ":" + Settings.auth_password
		headers.append("Authorization: Basic " + Marshalls.utf8_to_base64(creds))
		print("[API] Basic auth: %s" % Settings.auth_username)

	print("[API] %s %s" % [method, url])

	var body_string = ""
	if body != null:
		body_string = JSON.stringify(body)
		print("[API] Request body: %s" % body_string)

	var http_method = HTTPClient.METHOD_GET
	match method:
		"GET": http_method = HTTPClient.METHOD_GET
		"POST": http_method = HTTPClient.METHOD_POST
		"PUT": http_method = HTTPClient.METHOD_PUT
		"DELETE": http_method = HTTPClient.METHOD_DELETE

	var error = http.request(url, headers, http_method, body_string)

	if error != OK:
		push_error("[API] HTTP request failed: " + str(error))
		return {"error": true, "detail": {"code": "network_error", "details": {}}}

	var response      = await http.request_completed
	var status_code   = response[1]
	var resp_headers: PackedStringArray = response[2]
	var response_body = response[3]

	# Digest auth: challenge → compute → retry
	if status_code == 401 and Settings.auth_scheme == "digest" \
			and not Settings.auth_username.is_empty():
		var www_auth = _find_header(resp_headers, "www-authenticate")
		if www_auth.to_lower().begins_with("digest"):
			var auth_headers = headers.duplicate()
			auth_headers.append("Authorization: " + _build_digest_header(
					method, _extract_uri(url), www_auth))
			error = http.request(url, auth_headers, http_method, body_string)
			if error == OK:
				response      = await http.request_completed
				status_code   = response[1]
				response_body = response[3]

	print("[API] Response status: %d" % status_code)

	if status_code < 200 or status_code >= 300:
		# Handle 401 Unauthorized
		if status_code == 401:
			return {"error": true, "detail": {"code": "auth_required", "details": {}}}

		var error_text = response_body.get_string_from_utf8()
		var json = JSON.new()
		var parse_error = json.parse(error_text)

		# Parse BCD API error format: {"success": false, "error": "...", "error_code": "...", "context": {...}}
		if parse_error == OK and json.data is Dictionary:
			var error_data = json.data

			# BCD exceptions have error_code and context
			if error_data.has("error_code"):
				var code = str(error_data.error_code).to_lower()  # Convert ITEM_NOT_FOUND → item_not_found
				var context = error_data.get("context", {})
				return {"error": true, "detail": {"code": code, "details": context}}

			# Validation errors have details array
			if error_data.has("details") and error_data.details is Array:
				return {"error": true, "detail": {"code": "validation_error", "details": {}}}

		# Unknown error format - return generic error (no technical message)
		return {"error": true, "detail": {"code": "unknown_error", "details": {}}}

	var text = response_body.get_string_from_utf8()

	if text.is_empty():
		print("[API] Empty response body")
		return {}

	print("[API] Response body (first 200 chars): %s" % text.substr(0, 200))

	var json = JSON.new()
	var parse_error = json.parse(text)

	if parse_error != OK:
		push_error("[API] JSON parse error: " + json.get_error_message())
		return {"error": true, "detail": {"code": "parse_error", "details": {}}}

	var data_type = "null"
	if json.data is Array:
		data_type = "Array[%d]" % json.data.size()
	elif json.data is Dictionary:
		data_type = "Dictionary with keys: %s" % str(json.data.keys())
	elif json.data != null:
		data_type = str(typeof(json.data))

	print("[API] Parsed data type: %s" % data_type)

	if json.data != null:
		return json.data
	return {}
