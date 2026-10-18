# A book currently borrowed by the student, shown on the checkout screen.
class_name LoanSummary
extends VBoxContainer

const DATA = preload("res://src/utils/DataHelper.gd")

@onready var _cover_img: CoverImage = %CoverImage
@onready var _cover_placeholder: Label = %CoverPlaceholder
@onready var _title_lbl: Label = %TitleLabel
@onready var _due_lbl: Label = %DueLabel

func _ready() -> void:
	_cover_img.cover_loaded.connect(_on_cover_loaded)
	_cover_img.cover_failed.connect(_on_cover_failed)

func setup(loan: Dictionary) -> void:
	_title_lbl.text = DATA.display_title(loan)
	var due_date := DATA.text(loan, "due_date")
	var is_overdue := DATA.boolean(loan, "is_overdue")
	if is_overdue:
		_due_lbl.text = "⚠️ " + I18n.t("main_menu.overdue") + ": " + due_date
		_due_lbl.theme_type_variation = "LabelError"
	else:
		_due_lbl.text = "⏰ " + I18n.t("checkout.due_date", {"date": due_date})
		_due_lbl.theme_type_variation = "LabelSubtitle"

	_cover_img.cancel()
	_cover_img.texture = null
	_cover_img.visible = false
	_cover_placeholder.visible = true
	var cover_file := DATA.text(loan, "cover_image").strip_edges()
	if not cover_file.is_empty():
		_cover_img.load_cover(cover_file)

func _on_cover_loaded(_texture: Texture2D) -> void:
	_cover_img.visible = true
	_cover_placeholder.visible = false

func _on_cover_failed() -> void:
	_cover_img.visible = false
	_cover_placeholder.visible = true
