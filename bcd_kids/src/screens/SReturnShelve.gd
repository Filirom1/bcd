# Screen: Return Shelve — shown after a return to indicate where to shelve the book
extends Control

@onready var _bg: ColorRect = %Background
@onready var _title_lbl: Label = %TitleLabel
@onready var _book_title_lbl: Label = %BookTitleLabel
@onready var _shelf_title_lbl: Label = %ShelfTitleLabel
@onready var _shelf_lbl: Label = %ShelfLabel
@onready var _call_title_lbl: Label = %CallTitleLabel
@onready var _call_lbl: Label = %CallLabel
@onready var _notif_lbl: Label = %NotifLabel
@onready var _ok_btn: Button = %OkBtn

func _ready() -> void:
	_bg.color = ThemeManager.PRIMARY

	var data: Dictionary = GS.current_class.get("_temp_return_shelve", {})

	_title_lbl.text = I18n.t("return.shelve_title")
	_book_title_lbl.text = data.get("title", "")
	
	_shelf_title_lbl.text = I18n.t("return.shelf_label")
	_shelf_lbl.text = data.get("shelf", "-")
	if _shelf_lbl.text.is_empty():
		_shelf_lbl.text = "-"
	
	_call_title_lbl.text = I18n.t("return.call_num_label")
	_call_lbl.text = data.get("call_num", "-")
	if _call_lbl.text.is_empty():
		_call_lbl.text = "-"
	
	_notif_lbl.text = I18n.t("return.shelve_instruction")

	_ok_btn.text = I18n.t("common.ok")
	_ok_btn.pressed.connect(_go_back)
	_ok_btn.call_deferred("grab_focus")

	get_tree().create_timer(5.0).timeout.connect(_go_back)

func _go_back() -> void:
	Mgr.pop()

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") or event.is_action_pressed("ui_accept"):
		_go_back()
		get_viewport().set_input_as_handled()
