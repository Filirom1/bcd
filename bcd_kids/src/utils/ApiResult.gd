# Optional typed envelope for migrating callers away from the legacy API return shape.
class_name ApiResult
extends RefCounted

var ok := false
var data: Variant = null
var error_code := ""
var details: Dictionary = {}


static func success(value: Variant) -> ApiResult:
	var result := ApiResult.new()
	result.ok = true
	result.data = value
	return result


static func failure(code: String, context: Dictionary = {}) -> ApiResult:
	var result := ApiResult.new()
	result.ok = false
	result.error_code = code.to_lower()
	result.details = context.duplicate(true)
	return result


static func from_legacy(value: Variant) -> ApiResult:
	if value is Dictionary and value.has("error"):
		var detail = value.get("detail", {})
		if detail is Dictionary:
			var context = detail.get("details", {})
			return failure(
				str(detail.get("code", "unknown_error")),
				context if context is Dictionary else {}
			)
		return failure("unknown_error")
	return success(value)


func unwrap(default_value: Variant = null) -> Variant:
	return data if ok else default_value


func to_legacy() -> Variant:
	if ok:
		return data
	return {
		"error": true,
		"detail": {"code": error_code, "details": details.duplicate(true)},
	}
