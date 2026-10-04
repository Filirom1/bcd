# Shared translation mapping for structured API errors.
class_name ErrorMessages
extends RefCounted

const COMMON := {
	"network_error": "common.error_network",
	"insecure_auth_transport": "auth.insecure_transport",
	"unsupported_digest": "auth.unsupported_digest",
}

const DISCOVERY := {
	"auth_required": "auth.required",
	"insecure_auth_transport": "auth.insecure_transport",
	"unsupported_digest": "auth.unsupported_digest",
	"network_error": "server_discovery.connection_error",
}

const BORROWER := {
	"network_error": "common.error_network",
	"unknown_error": "common.error_network",
	"borrower_not_found": "name_input.not_found",
	"invalid_response": "common.error_unknown",
}

const RETURN := {
	"network_error": "common.error_network",
	"item_not_found": "return.error_not_found",
	"item_not_on_loan": "return.error_not_on_loan",
}

const CHECKOUT := {
	"network_error": "common.error_network",
	"loan_limit_exceeded": "checkout.error_limit",
	"loan_limit_warning_exceeded": "checkout.error_warning_limit",
	"item_already_on_loan": "checkout.error_already_loaned",
	"borrower_blocked": "checkout.error_blocked",
	"borrower_has_overdue": "checkout.error_overdue",
	"item_not_found": "checkout.error_not_found",
	"item_not_available": "checkout.error_not_available",
	"item_not_loanable": "checkout.error_not_loanable",
	"item_reserved_for_other": "checkout.error_reserved",
}

const HOLD := {
	"network_error": "common.error_network",
	"insecure_auth_transport": "auth.insecure_transport",
	"borrower_blocked": "hold.error_blocked",
	"hold_already_exists": "hold.error_duplicate",
	"no_items_for_record": "hold.error_no_items",
	"hold_limit_exceeded": "hold.error_limit",
}

const RENEW := {
	"network_error": "common.error_network",
	"no_renewable_items": "main_menu.renew_no_items",
}


static func code(result: Variant) -> String:
	if not (result is Dictionary):
		return "invalid_response"
	var detail = result.get("detail")
	if not (detail is Dictionary):
		return ""
	return str(detail.get("code", "")).to_lower()


static func details(result: Variant) -> Dictionary:
	if not (result is Dictionary):
		return {}
	var detail = result.get("detail")
	if not (detail is Dictionary):
		return {}
	var value = detail.get("details", {})
	return value if value is Dictionary else {}


static func translation_key(
		result: Variant,
		mapping: Dictionary,
		fallback: String = "common.error_unknown"
) -> String:
	var error_code := code(result)
	return str(mapping.get(error_code, fallback))


static func message(
		result: Variant,
		mapping: Dictionary,
		fallback: String = "common.error_unknown",
		extra: Dictionary = {}
) -> String:
	var parameters := details(result).duplicate(true)
	parameters.merge(extra, true)
	var key := translation_key(result, mapping, fallback)
	var i18n := _autoload("I18n")
	if i18n == null:
		return key
	return str(i18n.call("t", key, parameters))


static func _autoload(name: String) -> Node:
	var main_loop := Engine.get_main_loop()
	if main_loop is SceneTree:
		return (main_loop as SceneTree).get_root().get_node_or_null(name)
	return null
