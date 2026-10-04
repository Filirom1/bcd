class_name PopularBooksCache
extends RefCounted

## One small global cache used by the reading intro.
## It intentionally has no server key: the last successful connection wins.

const CACHE_PATH := "user://popular_books.json"
const DISPLAY_LIMIT := 5
const CACHE_LIMIT := 50

static func load_books() -> Array[String]:
	if not FileAccess.file_exists(CACHE_PATH):
		return []
	var file := FileAccess.open(CACHE_PATH, FileAccess.READ)
	if file == null:
		return []
	var parsed = JSON.parse_string(file.get_as_text())
	return normalize(parsed)

static func save_books(books) -> bool:
	var normalized := normalize(books)
	if normalized.is_empty():
		return false
	var file := FileAccess.open(CACHE_PATH, FileAccess.WRITE)
	if file == null:
		return false
	file.store_string(JSON.stringify(normalized))
	return true

static func normalize(value) -> Array[String]:
	var source = value
	if value is Dictionary:
		source = value.get("books", value.get("titles", []))
	if not source is Array:
		return []

	var result: Array[String] = []
	for entry in source:
		var title := ""
		if entry is Dictionary:
			title = str(entry.get("title", "")).strip_edges()
		else:
			title = str(entry).strip_edges()
		if title.is_empty() or result.has(title):
			continue
		result.append(title)
		if result.size() >= CACHE_LIMIT:
			break
	return result
