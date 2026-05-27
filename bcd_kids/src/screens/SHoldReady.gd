# Screen: Hold Ready — shown after a return when a hold is waiting
extends Control

@onready var _bg: ColorRect = %Background
@onready var _title_lbl: Label = %TitleLabel
@onready var _book_title_lbl: Label = %BookTitleLabel
@onready var _borrower_lbl: Label = %BorrowerLabel
@onready var _class_lbl: Label = %ClassLabel
@onready var _notif_lbl: Label = %NotifLabel
@onready var _ok_btn: Button = %OkBtn

func _ready() -> void:
	_bg.color = ThemeManager.WARNING if ThemeManager.has_method("get") else Color("F2BF33")
	_bg.color = Color("F2BF33")

	var data: Dictionary = GS.current_class.get("_temp_hold_ready", {})

	_title_lbl.text = I18n.t("return.hold_ready_title")
	_book_title_lbl.text = data.get("title", "")
	_borrower_lbl.text = data.get("borrower_name", "")
	_class_lbl.text = data.get("class_name", data.get("borrower_id", ""))
	_notif_lbl.text = I18n.t("return.hold_ready_instruction")

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
