# A successfully returned book shown in the return-session history.
class_name HistoryEntry
extends VBoxContainer

const DATA = preload("res://src/utils/DataHelper.gd")

@onready var _cover_img: CoverImage = %CoverImage
@onready var _cover_placeholder: Label = %CoverPlaceholder
@onready var _title_label: Label = %TitleLabel
@onready var _status_label: Label = %StatusLabel
@onready var _borrower_label: Label = %BorrowerLabel
@onready var _location_row: HBoxContainer = %LocationRow
@onready var _location_label: Label = %LocationLabel
@onready var _badges: HBoxContainer = %Badges

func _ready() -> void:
	_cover_img.cover_loaded.connect(_on_cover_loaded)
	_cover_img.cover_failed.connect(_on_cover_failed)

func setup(item: Dictionary) -> void:
	_title_label.text = DATA.text(item, "display_title", DATA.text(item, "title", I18n.t("common.unknown_title")))
	var was_late := DATA.boolean(item, "was_overdue")
	var days_overdue := DATA.integer(item, "days_overdue")
	_status_label.text = I18n.t("return.late", {"days": days_overdue}) if was_late else I18n.t("return.on_time")
	_status_label.theme_type_variation = "LabelWarning" if was_late else "LabelSuccess"
	var borrower_name := DATA.text(item, "borrower_name").strip_edges()
	_borrower_label.text = I18n.t("return.returned_by", {"name": borrower_name}) if not borrower_name.is_empty() else ""
	_borrower_label.visible = not borrower_name.is_empty()

	var shelf := DATA.text(item, "shelf_location").strip_edges()
	var call_number := DATA.text(item, "call_number").strip_edges()
	_location_row.visible = not shelf.is_empty() or not call_number.is_empty()
	if _location_row.visible:
		_location_label.text = I18n.t("return.ranger_a")
		BadgeHelper.populate_badges(_badges, shelf, call_number)

	_cover_img.cancel()
	_cover_img.texture = null
	_cover_img.visible = false
	_cover_placeholder.visible = true
	var cover_file := DATA.text(item, "cover_image").strip_edges()
	if not cover_file.is_empty():
		_cover_img.load_cover(cover_file)

func _on_cover_loaded(_texture: Texture2D) -> void:
	_cover_img.visible = true
	_cover_placeholder.visible = false

func _on_cover_failed() -> void:
	_cover_img.visible = false
	_cover_placeholder.visible = true
