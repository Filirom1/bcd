extends Node

@onready var _quit_dialog: ConfirmationDialog = %QuitDialog

func _ready() -> void:
	get_window().close_requested.connect(_on_window_close_requested)
	_quit_dialog.title = I18n.t("quit.title")
	_quit_dialog.dialog_text = I18n.t("quit.message")
	_quit_dialog.ok_button_text = I18n.t("quit.confirm")
	_quit_dialog.cancel_button_text = I18n.t("quit.cancel")
	_quit_dialog.confirmed.connect(_quit_application)

func _on_window_close_requested() -> void:
	if not _quit_dialog.visible:
		_quit_dialog.popup_centered()

func _quit_application() -> void:
	get_tree().quit()
