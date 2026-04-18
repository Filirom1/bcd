# Breadcrumb Component
class_name Breadcrumb
extends HBoxContainer

signal crumb_clicked(screen_name: String)

var _crumbs: Array = []

func _ready() -> void:
	add_theme_constant_override("separation", 8)

func set_path(crumbs: Array) -> void:
	_crumbs = crumbs
	_rebuild()

func _rebuild() -> void:
	for child in get_children():
		child.queue_free()

	for i in range(_crumbs.size()):
		var crumb = _crumbs[i]
		var is_last := (i == _crumbs.size() - 1)

		if crumb.get("clickable", false) and not is_last:
			var btn := Button.new()
			btn.text = crumb.text
			btn.flat = true
			btn.theme_type_variation = "ButtonBreadcrumb"
			var screen = crumb.get("screen", "")
			btn.pressed.connect(func(): crumb_clicked.emit(screen))
			add_child(btn)
		else:
			var lbl := Label.new()
			lbl.text = crumb.text
			lbl.theme_type_variation = "LabelMedium" if is_last else "LabelSubtitle"
			add_child(lbl)

		if not is_last:
			var sep := Label.new()
			sep.text = " > "
			sep.theme_type_variation = "LabelSubtitle"
			add_child(sep)
