# Screen 6bis: Hold Confirmation
extends Control

@onready var _bg: ColorRect = %Background
@onready var _title_lbl: Label = %TitleLabel
@onready var _book_title_lbl: Label = %BookTitleLabel
@onready var _authors_lbl: Label = %AuthorsLabel
@onready var _queue_lbl: Label = %QueueLabel
@onready var _notif_lbl: Label = %NotifLabel
@onready var _ok_btn: Button = %OkBtn

var _book_data: Dictionary

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_book_data = GS.current_class.get("_temp_book_data", {})
	var hold_result: Dictionary = GS.current_class.get("_temp_hold_result", {})

	_title_lbl.text = I18n.t("hold.confirmed")
	_book_title_lbl.text = _book_data.get("title", "")

	var authors = _book_data.get("authors", [])
	var authors_text := ", ".join(authors) if authors is Array and not authors.is_empty() else ""
	_authors_lbl.text = authors_text
	_authors_lbl.visible = not authors_text.is_empty()

	var queue_pos := int(hold_result.get("queue_position", 1))
	if queue_pos > 1:
		_queue_lbl.text = I18n.t("hold.position", {"position": queue_pos})
		_queue_lbl.visible = true

	_notif_lbl.text = I18n.t("hold.notification")

	var title: String = _book_data.get("title", "")
	if title.is_empty():
		Mgr.notify(I18n.t("hold.confirmed"), "success")
	else:
		Mgr.notify(I18n.t("hold.confirmed_with_title", {"title": title}), "success")

	_ok_btn.text = I18n.t("common.ok")
	_ok_btn.pressed.connect(_go_back)
	_ok_btn.call_deferred("grab_focus")

	get_tree().create_timer(3.0).timeout.connect(_go_back)

func _go_back() -> void:
	Mgr.pop()

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") or event.is_action_pressed("ui_accept"):
		_go_back()
		get_viewport().set_input_as_handled()
