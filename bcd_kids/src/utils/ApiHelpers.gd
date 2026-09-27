# Dependency-free helpers shared by the Godot API transport and UI.
class_name ApiHelpers
extends RefCounted


static func extract_uri(url: String) -> String:
	var parts = url.split("://", false, 1)
	if parts.size() < 2:
		return "/"
	var slash = parts[1].find("/")
	return parts[1].substr(slash) if slash != -1 else "/"


static func parse_digest_param(header: String, param: String) -> String:
	var idx = header.to_lower().find((param + "=").to_lower())
	if idx == -1:
		return ""
	var start = idx + param.length() + 1
	if start >= header.length():
		return ""
	if header[start] == '"':
		start += 1
		var end = header.find('"', start)
		return header.substr(start, end - start) if end != -1 else ""
	var end = header.find(",", start)
	return header.substr(start, (end if end != -1 else header.length()) - start).strip_edges()


static func md5(text: String) -> String:
	var context := HashingContext.new()
	context.start(HashingContext.HASH_MD5)
	context.update(text.to_utf8_buffer())
	return context.finish().hex_encode()


static func strip_api_suffix(url: String) -> String:
	var base := url.rstrip("/")
	if "/api/v1" in base:
		base = base.split("/api/v1")[0]
	return base
