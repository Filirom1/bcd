# Filter Panel Component
class_name FilterPanel
extends VBoxContainer

signal filters_changed(filters: Dictionary)

@onready var _type_label: Label = %TypeLabel
@onready var _genre_label: Label = %GenreLabel
@onready var _type_option: OptionButton = %TypeOption
@onready var _genre_option: OptionButton = %GenreOption
@onready var _available_checkbox: CheckBox = %AvailableCheckbox

func _ready() -> void:
	_type_option.item_selected.connect(func(_idx): _on_filter_changed())
	_available_checkbox.toggled.connect(func(_checked): _on_filter_changed())

func setup(types: Array) -> void:
	_type_label.text = I18n.t("search.filter_type")
	_available_checkbox.text = I18n.t("search.available_only")

	# Hide genre options as genre classification is removed
	_genre_label.hide()
	_genre_option.hide()

	_type_option.clear()
	_type_option.add_item(I18n.t("common.all"))
	for t in types:
		_type_option.add_item(str(t))

func _on_filter_changed() -> void:
	filters_changed.emit(get_filters())

func get_filters() -> Dictionary:
	var filters := {}
	if _type_option.selected > 0:
		filters["medium_type"] = _type_option.get_item_text(_type_option.selected)
	if _available_checkbox.button_pressed:
		filters["available_only"] = true
	return filters
