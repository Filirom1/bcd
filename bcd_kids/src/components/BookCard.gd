# Book Card Component
class_name BookCard
extends PanelContainer

const DATA = preload("res://src/utils/DataHelper.gd")

signal action_clicked(book_data: Dictionary)
signal detail_clicked(book_data: Dictionary)

@onready var _cover_img: CoverImage = %CoverImage
@onready var _cover_placeholder: Label = %CoverPlaceholder
@onready var _title_lbl: Label = %TitleLabel
@onready var _series_lbl: Label = %SeriesLabel
@onready var _authors_lbl: Label = %AuthorsLabel
@onready var _status_lbl: Label = %StatusLabel
@onready var _badges_row: HBoxContainer = %BadgesRow
@onready var _action_btn: Button = %ActionBtn
@onready var _detail_btn: Button = %DetailBtn

var book_data: Dictionary
var _action_signal_connected := false
var _detail_signal_connected := false

func _ready() -> void:
	_cover_img.cover_loaded.connect(_on_cover_texture_loaded)
	_cover_img.cover_failed.connect(_on_cover_failed)
	_detail_btn.text = "🔍 " + I18n.t("book_detail.detail")
	_action_btn.focus_entered.connect(func():
		ThemeManager.apply_focus_style(_action_btn)
	)
	_action_btn.focus_exited.connect(func():
		ThemeManager.remove_focus_style(_action_btn)
	)
	_detail_btn.focus_entered.connect(func():
		ThemeManager.apply_focus_style(_detail_btn)
	)
	_detail_btn.focus_exited.connect(func():
		ThemeManager.remove_focus_style(_detail_btn)
	)

func grab_first_focus() -> void:
	if _action_btn.visible:
		_action_btn.grab_focus()
	else:
		_detail_btn.grab_focus()

func setup(data: Dictionary, action_label: String, action_color: Color) -> void:
	book_data = data

	var available_copies := DATA.integer(data, "available_copies")
	var holds_count := DATA.integer(data, "active_holds_count")

	if available_copies > 0:
		_status_lbl.text = "🟢 " + I18n.t("search.status_available")
	elif holds_count > 0:
		_status_lbl.text = "🟡 " + I18n.t("search.status_reserved")
	else:
		_status_lbl.text = "🔴 " + I18n.t("search.status_on_loan")

	theme_type_variation = "PanelNeutral"

	_title_lbl.text = DATA.text(data, "title", I18n.t("common.unknown_title"))
	_set_series_text(data)

	var authors = data.get("authors", [])
	var authors_text := ", ".join(authors) if authors is Array and not authors.is_empty() else ""
	if authors_text.is_empty():
		authors_text = DATA.text(data, "publisher")
	_authors_lbl.text = authors_text
	_authors_lbl.visible = not authors_text.is_empty()

	BadgeHelper.populate_badges(
		_badges_row,
		DATA.text(data, "shelf_location"),
		DATA.text(data, "call_number")
	)

	_cover_img.cancel()
	_cover_img.texture = null
	_cover_img.visible = false
	_cover_placeholder.visible = true
	var cover_file := DATA.text(data, "cover_image").strip_edges()
	if not cover_file.is_empty():
		_cover_img.load_cover(cover_file)

	_action_btn.visible = not action_label.is_empty()
	if not action_label.is_empty():
		_action_btn.text = action_label
		_action_btn.add_theme_color_override("font_color", action_color)
		_action_btn.add_theme_color_override("font_pressed_color", ThemeManager.BG_WHITE)
		if not _action_signal_connected:
			_action_btn.pressed.connect(func(): action_clicked.emit(book_data))
			_action_signal_connected = true

	if not _detail_signal_connected:
		_detail_btn.pressed.connect(func(): detail_clicked.emit(book_data))
		_detail_signal_connected = true

func _set_series_text(data: Dictionary) -> void:
	var collection := DATA.text(data, "collection").strip_edges()
	var series_number := DATA.text(data, "series_number").strip_edges()

	if not collection.is_empty() and not series_number.is_empty():
		_series_lbl.text = I18n.t("search.series_with_number", {
			"series": collection,
			"number": series_number,
		})
	elif not collection.is_empty():
		_series_lbl.text = I18n.t("search.series", {"series": collection})
	elif not series_number.is_empty():
		_series_lbl.text = I18n.t("search.series_number_only", {"number": series_number})
	else:
		_series_lbl.text = ""

	_series_lbl.visible = not _series_lbl.text.is_empty()

func _on_cover_texture_loaded(_texture: Texture2D) -> void:
	_cover_img.visible = true
	_cover_placeholder.visible = false

func _on_cover_failed() -> void:
	_cover_img.visible = false
	_cover_placeholder.visible = true
