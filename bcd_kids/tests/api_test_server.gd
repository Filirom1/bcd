# Minimal in-process HTTP/1.1 fixture used by api_transport_test.gd.
#
# Keeping the fixture in Godot (rather than starting a Python process) makes the
# transport tests deterministic in CI and exercises the real HTTPRequest node.
extends Node

var _server := TCPServer.new()
var _clients: Array = []
var _routes: Dictionary = {}
var requests: Array = []
var port := 0


func start() -> bool:
	# Port zero asks the OS for an unused local port.  Godot exposes the selected
	# port through TCPServer.get_local_port().
	var error := _server.listen(0, "127.0.0.1")
	if error != OK:
		return false
	port = _server.get_local_port()
	return port > 0


func stop() -> void:
	for state in _clients:
		var peer: StreamPeerTCP = state.get("peer")
		if peer != null:
			peer.disconnect_from_host()
	_clients.clear()
	_server.stop()


func enqueue(
	path: String,
	status_code: int,
	body: String = "",
	extra_headers: Dictionary = {}
) -> void:
	if not _routes.has(path):
		_routes[path] = []
	_routes[path].append({
		"status": status_code,
		"body": body,
		"headers": extra_headers,
	})


func clear_routes() -> void:
	_routes.clear()


func last_request() -> Dictionary:
	return requests.back() if not requests.is_empty() else {}


func _process(_delta: float) -> void:
	while _server.is_connection_available():
		_clients.append({
			"peer": _server.take_connection(),
			"buffer": PackedByteArray(),
		})

	for index in range(_clients.size() - 1, -1, -1):
		var state: Dictionary = _clients[index]
		var peer: StreamPeerTCP = state.get("peer")
		if peer == null:
			_clients.remove_at(index)
			continue
		peer.poll()
		if peer.get_status() == StreamPeerTCP.STATUS_ERROR or peer.get_status() == StreamPeerTCP.STATUS_NONE:
			_clients.remove_at(index)
			continue
		if state.get("response_sent", false):
			var close_ticks := int(state.get("close_ticks", 0)) - 1
			if close_ticks <= 0:
				peer.disconnect_from_host()
				_clients.remove_at(index)
			else:
				state["close_ticks"] = close_ticks
				_clients[index] = state
			continue

		var available := peer.get_available_bytes()
		if available > 0:
			var packet: Array = peer.get_data(available)
			if packet[0] != OK:
				_clients.remove_at(index)
				continue
			var buffer: PackedByteArray = state.get("buffer", PackedByteArray())
			buffer.append_array(packet[1])
			state["buffer"] = buffer
			_clients[index] = state

		var request := _parse_request(state.get("buffer", PackedByteArray()))
		if request.is_empty():
			continue
		requests.append(request)
		_respond(peer, request)
		# Keep the peer alive for a couple of frames.  HTTPRequest can otherwise
		# observe the close before the final packet has reached its parser on
		# slower CI machines.
		state["response_sent"] = true
		state["close_ticks"] = 2
		_clients[index] = state


func _parse_request(buffer: PackedByteArray) -> Dictionary:
	if buffer.is_empty():
		return {}
	# Request headers are ASCII.  The body is decoded only after the declared
	# Content-Length has arrived, so JSON bodies remain intact.
	var text := buffer.get_string_from_utf8()
	var separator := text.find("\r\n\r\n")
	if separator == -1:
		return {}
	var header_text := text.substr(0, separator)
	var lines := header_text.split("\r\n")
	if lines.is_empty():
		return {}
	var request_parts := lines[0].split(" ")
	if request_parts.size() < 2:
		return {}

	var headers: Dictionary = {}
	for line in lines.slice(1):
		var colon := line.find(":")
		if colon == -1:
			continue
		headers[line.substr(0, colon).strip_edges().to_lower()] = line.substr(colon + 1).strip_edges()

	var content_length := int(headers.get("content-length", "0"))
	var body_offset := separator + 4
	if buffer.size() < body_offset + content_length:
		return {}
	var body := ""
	if content_length > 0:
		body = buffer.slice(body_offset, body_offset + content_length).get_string_from_utf8()

	var target: String = request_parts[1]
	return {
		"method": request_parts[0],
		"target": target,
		"path": target.split("?", false, 1)[0],
		"headers": headers,
		"body": body,
	}


func _respond(peer: StreamPeerTCP, request: Dictionary) -> void:
	var path: String = request.get("path", "")
	var response: Dictionary = {}
	var queue: Array = _routes.get(path, [])
	if not queue.is_empty():
		response = queue.pop_front()
		_routes[path] = queue
	else:
		response = {"status": 404, "body": "", "headers": {}}

	var status_code := int(response.get("status", 500))
	var body_value = response.get("body", "")
	var body: PackedByteArray
	if body_value is PackedByteArray:
		body = body_value
	else:
		body = str(body_value).to_utf8_buffer()
	var reason := _reason_phrase(status_code)
	var head := "HTTP/1.1 %d %s\r\nContent-Length: %d\r\nConnection: close\r\n" % [
		status_code,
		reason,
		body.size(),
	]
	for header_name in response.get("headers", {}).keys():
		head += "%s: %s\r\n" % [header_name, response.headers[header_name]]
	head += "\r\n"
	var packet := head.to_utf8_buffer()
	packet.append_array(body)
	peer.put_data(packet)
	peer.disconnect_from_host()


func _reason_phrase(status_code: int) -> String:
	match status_code:
		200: return "OK"
		201: return "Created"
		204: return "No Content"
		401: return "Unauthorized"
		404: return "Not Found"
		422: return "Unprocessable Entity"
		500: return "Internal Server Error"
		_: return "Test Response"
