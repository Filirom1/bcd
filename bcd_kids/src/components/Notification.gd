# Notification (toast) Component
class_name Notification
extends PanelContainer

@onready var _label: Label = %MessageLabel

func setup(text: String, type: String) -> void:
	_label.text = text
	match type:
		"success":
			theme_type_variation = "PanelNotificationSuccess"
		"error":
			theme_type_variation = "PanelNotificationError"
		"warning":
			theme_type_variation = "PanelNotificationWarning"
		_:
			theme_type_variation = "PanelNotificationSuccess"
