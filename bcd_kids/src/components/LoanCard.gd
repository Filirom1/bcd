# Loan Card Component
class_name LoanCard
extends PanelContainer

const DATA = preload("res://src/utils/DataHelper.gd")

signal renew_clicked(item_id: String)
signal title_clicked(loan: Dictionary)

@onready var _cover_img: CoverImage = %CoverImage
@onready var _cover_placeholder: Label = %CoverPlaceholder
@onready var _title_lbl: Label = %TitleLabel
@onready var _authors_lbl: Label = %AuthorsLabel
@onready var _due_lbl: Label = %DueLabel
@onready var _renew_btn: Button = %RenewBtn

var _loan_data: Dictionary
var _renew_signal_connected := false
var _cover_click_signals_connected := false

func _ready() -> void:
	_cover_img.cover_loaded.connect(_on_cover_texture_loaded)
	_cover_img.cover_failed.connect(_on_cover_failed)
	_renew_btn.focus_entered.connect(func():
		ThemeManager.apply_focus_style(_renew_btn)
	)
	_renew_btn.focus_exited.connect(func():
		ThemeManager.remove_focus_style(_renew_btn)
	)

func setup(loan: Dictionary) -> void:
	_loan_data = loan
	var is_overdue := DATA.boolean(loan, "is_overdue")
	var due_date: String = DATA.text(loan, "due_date")

	_title_lbl.text = DATA.display_title(loan)

	var authors = loan.get("authors", [])
	var authors_text: String
	if authors is Array:
		authors_text = ", ".join(authors) if not authors.is_empty() else ""
	else:
		authors_text = str(authors) if authors != null else ""
	if authors_text.is_empty():
		authors_text = DATA.text(loan, "publisher")
	_authors_lbl.text = authors_text
	_authors_lbl.visible = not _authors_lbl.text.is_empty()

	if is_overdue:
		_due_lbl.text = "⚠️ " + I18n.t("main_menu.overdue") + ": " + due_date
		_due_lbl.theme_type_variation = "LabelError"
		theme_type_variation = "PanelError"
	else:
		_due_lbl.text = "⏰ " + due_date
		_due_lbl.theme_type_variation = "LabelSubtitle"
		theme_type_variation = "PanelSuccess"

	_renew_btn.text = "🔄 " + I18n.t("main_menu.renew_button")
	if not _renew_signal_connected:
		_renew_btn.pressed.connect(func(): renew_clicked.emit(str(_loan_data.get("item_id", ""))))
		_renew_signal_connected = true
	
	# Cover thumbnail — click opens the book detail screen.
	var cover_file: String = DATA.text(loan, "cover_image")
	_show_placeholder()
	if not cover_file.is_empty():
		_load_cover(cover_file)

	if not _cover_click_signals_connected:
		_cover_img.gui_input.connect(func(event):
			if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
				title_clicked.emit(_loan_data)
		)
		_cover_placeholder.gui_input.connect(func(event):
			if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
				title_clicked.emit(_loan_data)
		)
		_cover_click_signals_connected = true

func _load_cover(filename: String) -> void:
	_cover_img.load_cover(filename)

func _on_cover_texture_loaded(_texture: Texture2D) -> void:
	_cover_img.visible = true
	_cover_placeholder.visible = false

func _on_cover_failed() -> void:
	_show_placeholder()

func _show_placeholder() -> void:
	_cover_img.visible = false
	_cover_placeholder.visible = true
