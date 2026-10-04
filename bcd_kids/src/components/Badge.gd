# Visual badge used for shelf and call-number metadata.
class_name Badge
extends PanelContainer

# The base shape and spacing are editable in Badge.tscn. Only the background
# and border colors depend on the server-provided catalog settings at runtime.
@export var square_style: StyleBoxFlat
@export var pill_style: StyleBoxFlat


func setup(value: String, background: Color, radius: int, text_color: Color) -> void:
	var label := get_node("Label") as Label
	label.text = value
	label.add_theme_color_override("font_color", text_color)

	var base_style := pill_style if radius >= 20 else square_style
	if base_style == null:
		base_style = get_theme_stylebox("panel") as StyleBoxFlat
	if base_style == null:
		return

	# Duplicate the editable scene resource because each badge receives its own
	# data-dependent color without mutating the shared resource.
	var style := base_style.duplicate() as StyleBoxFlat
	style.bg_color = background if background.a >= 0.01 else Color(0, 0, 0, 0)
	style.border_color = text_color
	add_theme_stylebox_override("panel", style)
