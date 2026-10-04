# BadgeHelper — colored badge nodes for shelf location and Dewey call number.
#
# Convention (mirrors web UI useItemBadge.js):
#   - Shelf location : corner_radius = 4  (square)
#   - Dewey call number : corner_radius = 20 (pill)
#
# Color rules:
#   - Entry found with hex color  → colored background, auto text color
#   - Entry found without color, or not found → transparent + 1px border
#   - Field absent/empty → return null (caller shows nothing)
#
# Usage:
#   var node = BadgeHelper.make_shelf_badge("Romans")
#   if node: hbox.add_child(node)
#
#   var node = BadgeHelper.make_cote_badge("843.91 SAI")
#   if node: hbox.add_child(node)

class_name BadgeHelper

const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")
const BADGE_SCENE = preload("res://src/components/Badge.tscn")


# Returns Color.BLACK or Color.WHITE for readable text on bg.
static func auto_text_color(bg: Color) -> Color:
	var lum := 0.299 * bg.r + 0.587 * bg.g + 0.114 * bg.b
	return Color.BLACK if lum > 0.55 else Color.WHITE


static func _settings() -> Dictionary:
	var main_loop := Engine.get_main_loop()
	if main_loop is SceneTree:
		var state := (main_loop as SceneTree).get_root().get_node_or_null("GS")
		if state != null:
			var value = state.get("settings")
			return value if value is Dictionary else {}
	return {}


# Shelf location color from the global settings store.
# The API response contains this setting as an Array of Dictionaries.
# Returns transparent when absent or no color is defined.
static func get_shelf_color(label: String) -> Color:
	var locations: Array = _settings().get("catalog_shelf_locations", [])
	for entry in locations:
		if entry is Dictionary and str(entry.get("label", "")).strip_edges() == label.strip_edges():
			var hex := str(entry.get("color", "")).strip_edges()
			return Color.html(hex) if not hex.is_empty() else Color(0, 0, 0, 0)
	return Color(0, 0, 0, 0)


# Dewey class color from GS.settings["dewey_colors"] (10-element Array).
static func get_dewey_color(call_number: String) -> Color:
	var settings := _settings()
	if settings.get("dewey_colors_enabled", true) == false:
		return Color(0, 0, 0, 0)
	var trimmed := call_number.strip_edges()
	if trimmed.is_empty() or trimmed[0] < "0" or trimmed[0] > "9":
		return Color(0, 0, 0, 0)
	var colors: Array = settings.get("dewey_colors", [])
	var idx := int(trimmed[0])
	if colors.size() < 10 or colors[idx] == null:
		return Color(0, 0, 0, 0)
	var hex := str(colors[idx]).strip_edges()
	return Color.html(hex) if not hex.is_empty() else Color(0, 0, 0, 0)


static func _theme_text_color() -> Color:
	var main_loop := Engine.get_main_loop()
	if main_loop is SceneTree:
		var manager := (main_loop as SceneTree).get_root().get_node_or_null("ThemeManager")
		if manager != null:
			return manager.get("TEXT")
	return Color("#1f2937")


# Build a badge PanelContainer from the editable Badge scene.
# bg.a < 0.01 → transparent background + 1px border in the theme text color.
static func _make_badge(text: String, bg: Color, radius: int) -> PanelContainer:
	var text_color := _theme_text_color() if bg.a < 0.01 else auto_text_color(bg)
	var panel := BADGE_SCENE.instantiate() as PanelContainer
	panel.call("setup", text, bg, radius, text_color)
	return panel


# Square badge (radius=4) for shelf location.
# Returns null if label is empty.
static func make_shelf_badge(label: String) -> PanelContainer:
	if label.is_empty():
		return null
	return _make_badge(label, get_shelf_color(label), 4)


# Pill badge (radius=20) for Dewey call number.
# Returns null if call_number is empty.
static func make_cote_badge(call_number: String) -> PanelContainer:
	if call_number.is_empty():
		return null
	return _make_badge(call_number, get_dewey_color(call_number), 20)


# Populate an HBoxContainer with shelf + cote badges.
# Clears existing children. Hides the row if no badges.
static func populate_badges(row: HBoxContainer, shelf: String, call_number: String) -> void:
	NODE_HELPER.clear_children(row)
	var visible := false
	var shelf_badge := make_shelf_badge(shelf)
	if shelf_badge:
		row.add_child(shelf_badge)
		visible = true
	var cote_badge := make_cote_badge(call_number)
	if cote_badge:
		row.add_child(cote_badge)
		visible = true
	row.visible = visible
