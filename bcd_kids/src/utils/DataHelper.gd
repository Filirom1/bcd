# Shared helpers for safely reading nullable API response fields.
class_name DataHelper
extends RefCounted


static func text(data: Dictionary, key: String, fallback: String = "") -> String:
	var value = data.get(key)
	return fallback if value == null else display_value(value)


static func display_value(value: Variant) -> String:
	if typeof(value) == TYPE_FLOAT:
		var numeric_value: float = value
		if is_finite(numeric_value) and numeric_value == floor(numeric_value):
			return str(int(numeric_value))
	return str(value)


static func display_title(data: Dictionary) -> String:
	var display := text(data, "display_title")
	return display if not display.is_empty() else text(data, "title")


static func integer(data: Dictionary, key: String, fallback: int = 0) -> int:
	var value = data.get(key)
	return fallback if value == null else int(value)


static func boolean(data: Dictionary, key: String, fallback: bool = false) -> bool:
	var value = data.get(key)
	return fallback if value == null else bool(value)


static func array(data: Dictionary, key: String) -> Array:
	var value = data.get(key)
	return value if value is Array else []
