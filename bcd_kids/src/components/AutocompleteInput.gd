# Autocomplete Input Component
class_name AutocompleteInput
extends VBoxContainer

signal search_submitted(query: String)

@onready var _line_edit: LineEdit = %SearchInput

func _ready() -> void:
	_line_edit.keep_editing_on_text_submit = true
	_line_edit.text_submitted.connect(_on_text_submitted)

func _on_text_submitted(text: String) -> void:
	search_submitted.emit(text)

func set_placeholder(text: String) -> void:
	_line_edit.placeholder_text = text

func get_text() -> String:
	return _line_edit.text

func clear() -> void:
	_line_edit.clear()

func focus_input() -> void:
	_line_edit.call_deferred("grab_focus")

func is_input_focused() -> bool:
	return _line_edit.has_focus()
