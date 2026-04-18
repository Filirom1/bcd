# Loan Card Component
class_name LoanCard
extends PanelContainer

signal return_clicked(item_id: String)

@onready var _icon_lbl: Label = %IconLabel
@onready var _title_lbl: Label = %TitleLabel
@onready var _authors_lbl: Label = %AuthorsLabel
@onready var _due_lbl: Label = %DueLabel
@onready var _return_btn: Button = %ReturnBtn

func setup(loan: Dictionary) -> void:
	var item_id: String = loan.get("item_id", "")
	var is_overdue: bool = loan.get("is_overdue", false)
	var due_date: String = loan.get("due_date", "")

	_title_lbl.text = loan.get("display_title", loan.get("title", ""))

	var authors = loan.get("authors", [])
	var authors_text := ", ".join(authors) if authors is Array and not authors.is_empty() else ""
	if authors_text.is_empty():
		authors_text = loan.get("publisher", "")
	_authors_lbl.text = authors_text
	_authors_lbl.visible = not _authors_lbl.text.is_empty()

	if is_overdue:
		_due_lbl.text = "⚠️ " + I18n.t("main_menu.overdue") + ": " + due_date
		_due_lbl.theme_type_variation = "LabelError"
		_icon_lbl.theme_type_variation = "LabelError"
		theme_type_variation = "PanelError"
	else:
		_due_lbl.text = "⏰ " + due_date
		_due_lbl.theme_type_variation = "LabelSubtitle"
		theme_type_variation = "PanelSuccess"

	_return_btn.text = "✓ " + I18n.t("main_menu.return_button")
	_return_btn.pressed.connect(func(): return_clicked.emit(item_id))
