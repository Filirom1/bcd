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
	_genre_option.item_selected.connect(func(_idx): _on_filter_changed())
	_available_checkbox.toggled.connect(func(_checked): _on_filter_changed())

func setup(types: Array, genres: Array) -> void:
	_type_label.text = I18n.t("search.filter_type")
	_genre_label.text = I18n.t("search.filter_genre")
	_available_checkbox.text = I18n.t("search.available_only")

	_type_option.clear()
	_type_option.add_item(I18n.t("common.all"))
	for t in types:
		_type_option.add_item(str(t))

	_genre_option.clear()
	_genre_option.add_item(I18n.t("common.all"))
	for g in genres:
		_genre_option.add_item(str(g))

func _on_filter_changed() -> void:
	filters_changed.emit(get_filters())

func get_filters() -> Dictionary:
	var filters := {}
	if _type_option.selected > 0:
		filters["medium_type"] = _type_option.get_item_text(_type_option.selected)
	if _genre_option.selected > 0:
		filters["genre"] = _genre_option.get_item_text(_genre_option.selected)
	if _available_checkbox.button_pressed:
		filters["available_only"] = true
	return filters
