# Breadcrumb Component
class_name Breadcrumb
extends HBoxContainer

signal crumb_clicked(screen_name: String)

const BREADCRUMB_BUTTON = preload("res://src/components/BreadcrumbButton.tscn")
const BREADCRUMB_LABEL = preload("res://src/components/BreadcrumbLabel.tscn")
const BREADCRUMB_SEPARATOR = preload("res://src/components/BreadcrumbSeparator.tscn")
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")

var _crumbs: Array = []

func _ready() -> void:
	add_theme_constant_override("separation", 8)

func set_path(crumbs: Array) -> void:
	_crumbs = crumbs
	_rebuild()

func _rebuild() -> void:
	NODE_HELPER.clear_children(self)

	for i in range(_crumbs.size()):
		var crumb: Dictionary = _crumbs[i]
		var is_last := i == _crumbs.size() - 1
		var part: Control
		if crumb.get("clickable", false) and not is_last:
			var button := BREADCRUMB_BUTTON.instantiate() as Button
			button.text = str(crumb.get("text", ""))
			var screen := str(crumb.get("screen", ""))
			button.pressed.connect(func(): crumb_clicked.emit(screen))
			part = button
		else:
			var label := BREADCRUMB_LABEL.instantiate() as Label
			label.text = str(crumb.get("text", ""))
			label.theme_type_variation = "LabelMedium" if is_last else "LabelSubtitle"
			part = label
		add_child(part)

		if not is_last:
			add_child(BREADCRUMB_SEPARATOR.instantiate())
