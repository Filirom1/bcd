# Book Card Component
class_name BookCard
extends PanelContainer

signal action_clicked(book_data: Dictionary)
signal detail_clicked(book_data: Dictionary)

@onready var _title_lbl: Label = %TitleLabel
@onready var _authors_lbl: Label = %AuthorsLabel
@onready var _status_lbl: Label = %StatusLabel
@onready var _badges_row: HBoxContainer = %BadgesRow
@onready var _action_btn: Button = %ActionBtn
@onready var _detail_btn: Button = %DetailBtn

var book_data: Dictionary

func _ready() -> void:
	_action_btn.focus_entered.connect(func():
		_action_btn.add_theme_stylebox_override("normal", _action_btn.get_theme_stylebox("hover"))
		_action_btn.add_theme_color_override("font_color", ThemeManager.TEXT)
	)
	_action_btn.focus_exited.connect(func():
		_action_btn.remove_theme_stylebox_override("normal")
		_action_btn.remove_theme_color_override("font_color")
	)
	_detail_btn.focus_entered.connect(func():
		_detail_btn.add_theme_stylebox_override("normal", _detail_btn.get_theme_stylebox("hover"))
		_detail_btn.add_theme_color_override("font_color", ThemeManager.TEXT)
	)
	_detail_btn.focus_exited.connect(func():
		_detail_btn.remove_theme_stylebox_override("normal")
		_detail_btn.remove_theme_color_override("font_color")
	)

func grab_first_focus() -> void:
	if _action_btn.visible:
		_action_btn.grab_focus()
	else:
		_detail_btn.grab_focus()

func setup(data: Dictionary, action_label: String, action_color: Color) -> void:
	book_data = data

	var available_copies := int(data.get("available_copies", 0))
	var holds_count := int(data.get("active_holds_count", 0))

	if available_copies > 0:
		_status_lbl.text = "🟢"
	elif holds_count > 0:
		_status_lbl.text = "🟡"
	else:
		_status_lbl.text = "🔴"

	theme_type_variation = "PanelNeutral"

	_title_lbl.text = data.get("title", "Unknown")

	var authors = data.get("authors", [])
	var authors_text := ", ".join(authors) if authors is Array and not authors.is_empty() else ""
	if authors_text.is_empty():
		authors_text = data.get("publisher", "")
	_authors_lbl.text = authors_text
	_authors_lbl.visible = not authors_text.is_empty()

	var _shelf_loc = data.get("shelf_location")
	var _call_num = data.get("call_number")
	BadgeHelper.populate_badges(
		_badges_row,
		str(_shelf_loc) if _shelf_loc != null else "",
		str(_call_num) if _call_num != null else ""
	)

	if action_label.is_empty():
		_action_btn.visible = false
	else:
		_action_btn.text = action_label
		_action_btn.add_theme_color_override("font_color", action_color)
		_action_btn.add_theme_color_override("font_pressed_color", ThemeManager.BG_WHITE)
		_action_btn.pressed.connect(func(): action_clicked.emit(book_data))

	_detail_btn.pressed.connect(func(): detail_clicked.emit(book_data))
	
