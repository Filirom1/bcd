# Screen 2bis: Name Choice (when duplicates)
# Note: Currently handled inline in SNameInput, but kept for future use
extends Control

@onready var _bg: ColorRect = %Background

func _ready() -> void:
	_bg.color = ThemeManager.BG
