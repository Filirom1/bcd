# Screen: Hold Ready — shown after a return when a hold is waiting
extends Control

const DATA = preload("res://src/utils/DataHelper.gd")

@onready var _bg: ColorRect = %Background
@onready var _title_lbl: Label = %TitleLabel
@onready var _book_title_lbl: Label = %BookTitleLabel
@onready var _borrower_lbl: Label = %BorrowerLabel
@onready var _class_lbl: Label = %ClassLabel
@onready var _notif_lbl: Label = %NotifLabel
@onready var _ok_btn: Button = %OkBtn

func _ready() -> void:
	_bg.color = ThemeManager.WARNING

	var data: Dictionary = GS.get_nav_param("hold_ready", {})

	_title_lbl.text = I18n.t("return.hold_ready_title")
	_book_title_lbl.text = DATA.text(data, "title")
	_borrower_lbl.text = DATA.text(data, "borrower_name")
	var class_label := DATA.text(data, "class_name")
	_class_lbl.text = class_label if not class_label.is_empty() else DATA.text(data, "borrower_id")
	_notif_lbl.text = I18n.t("return.hold_ready_instruction")

	_ok_btn.text = I18n.t("common.ok")
	_ok_btn.pressed.connect(_go_back)
	_ok_btn.call_deferred("grab_focus")


func _go_back() -> void:
	GS.clear_nav_param("hold_ready")
	Mgr.pop()

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") or event.is_action_pressed("ui_accept"):
		var viewport := get_viewport()
		if viewport != null:
			viewport.set_input_as_handled()
		_go_back()
