# Shared cover image loader and decoder.
class_name CoverImage
extends TextureRect

signal cover_loaded(texture: Texture2D)
signal cover_failed

const REQUEST_TIMEOUT_SECONDS := 5.0
var _request_id := 0

func load_cover(filename: String) -> void:
	_request_id += 1
	var request_id := _request_id
	texture = null
	var api := get_tree().root.get_node_or_null("API")
	var url: String = str(api.call("get_cover_url", filename)) if api != null else ""
	if url.is_empty():
		cover_failed.emit()
		return

	var request := HTTPRequest.new()
	request.timeout = REQUEST_TIMEOUT_SECONDS
	add_child(request)
	var request_error := request.request(url)
	if request_error != OK:
		request.queue_free()
		if request_id == _request_id:
			cover_failed.emit()
		return

	var response: Array = await request.request_completed
	request.queue_free()
	if not is_inside_tree() or request_id != _request_id:
		return
	if response[0] != HTTPRequest.RESULT_SUCCESS or response[1] < 200 or response[1] >= 300:
		cover_failed.emit()
		return

	var decoded := texture_from_response(response[0], response[1], response[3])
	if decoded == null:
		cover_failed.emit()
		return
	texture = decoded
	cover_loaded.emit(decoded)

static func texture_from_response(result: int, status: int, body: PackedByteArray) -> Texture2D:
	if result != HTTPRequest.RESULT_SUCCESS or status < 200 or status >= 300:
		return null
	return texture_from_buffer(body)

static func texture_from_buffer(body: PackedByteArray) -> Texture2D:
	# Check the file signatures first. Besides being cheaper, this avoids noisy
	# decoder errors for empty or non-image API responses.
	var is_jpeg := body.size() >= 2 and body[0] == 0xff and body[1] == 0xd8
	var is_png := body.size() >= 8 and body.slice(0, 8) == PackedByteArray([
		0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a
	])
	if not is_jpeg and not is_png:
		return null

	var image := Image.new()
	var error := image.load_jpg_from_buffer(body) if is_jpeg else image.load_png_from_buffer(body)
	if error != OK:
		return null
	return ImageTexture.create_from_image(image)

func cancel() -> void:
	_request_id += 1
