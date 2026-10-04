# Shared circulation operations for student-facing screens.
class_name CirculationHelper
extends RefCounted

const DATA = preload("res://src/utils/DataHelper.gd")

static func display_title(data: Dictionary) -> String:
	return DATA.display_title(data)

static func hold_ready_payload(item: Dictionary) -> Dictionary:
	var hold_ready = item.get("hold_ready", null)
	if not (hold_ready is Dictionary):
		return {}
	return {
		"title": display_title(item),
		"borrower_name": DATA.text(hold_ready, "borrower_name"),
		"class_name": DATA.text(hold_ready, "class_name"),
		"borrower_id": DATA.text(hold_ready, "borrower_id"),
	}

static func apply_loans_result(result, borrower: Dictionary) -> bool:
	if not (result is Dictionary) or result.has("error"):
		return false
	var state := _autoload("GS")
	var loans := DATA.array(result, "loans")
	state.set("current_loans", loans)
	borrower["current_loans_count"] = loans.size()
	return true

static func borrower_breadcrumb(final_text: String, include_borrower: bool = true) -> Array:
	var state := _autoload("GS")
	var current_class: Dictionary = state.get("current_class") if state.get("current_class") is Dictionary else {}
	var path := [
		{"text": str(state.get("library_name")), "screen": "class_select", "clickable": true},
		{"text": DATA.text(current_class, "name"), "screen": "class_select", "clickable": true},
	]
	var borrower: Dictionary = state.get("current_borrower")
	var borrower_name := "%s %s" % [DATA.text(borrower, "first_name"), DATA.text(borrower, "last_name")]
	if include_borrower:
		path.append({"text": borrower_name, "screen": "main_menu", "clickable": true})
	path.append({"text": final_text, "screen": "", "clickable": false})
	return path

static func update_counter(label: Label, borrower: Dictionary) -> void:
	var current := DATA.integer(borrower, "current_loans_count")
	var limit := DATA.integer(borrower, "loan_limit", 3)
	var warning_limit := DATA.integer(borrower, "loan_limit_warning")
	var i18n := _autoload("I18n")
	label.text = i18n.call("t", "main_menu.books_count", {"current": current, "limit": limit})
	var theme_manager := _autoload("ThemeManager")
	if current >= limit:
		label.add_theme_color_override("font_color", theme_manager.get("ERROR"))
	elif warning_limit > 0 and current >= warning_limit:
		label.add_theme_color_override("font_color", theme_manager.get("WARNING"))
	else:
		label.remove_theme_color_override("font_color")

static func refresh_loans(borrower_id: String):
	# The caller applies the result only after its navigation-generation check.
	# Keeping mutation out of this helper prevents an old screen from restoring
	# stale loans after the borrower or server has changed.
	return await _autoload("API").call("get_current_loans", borrower_id)

static func return_book(item_id: String):
	return await _autoload("API").call("return_items", [item_id])

static func renew_book(item_id: String, borrower_id: String):
	return await _autoload("API").call("renew_items", borrower_id, [item_id])

static func present_hold_ready(payload: Dictionary) -> bool:
	if payload.is_empty():
		return false
	_autoload("GS").call("set_nav_param", "hold_ready", payload)
	_autoload("Mgr").call("push", "hold_ready")
	return true

static func _autoload(name: String) -> Node:
	var main_loop := Engine.get_main_loop()
	if main_loop is SceneTree:
		var node := (main_loop as SceneTree).get_root().get_node_or_null(name)
		if node != null:
			return node
	return null
