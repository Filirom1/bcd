# Bibliographic field row. The layout is kept in FieldRow.tscn so it can be
# adjusted in the Godot editor without changing the detail screen logic.
class_name FieldRow
extends HBoxContainer

@onready var _key_label: Label = %KeyLabel
@onready var _value_label: Label = %ValueLabel
@onready var _badges: HBoxContainer = %Badges

func setup(label: String, value: String) -> void:
	_key_label.text = label + " :"
	_value_label.text = value
	_value_label.visible = not value.is_empty()
	_badges.visible = false

func setup_location(label: String, shelf: String, call_number: String) -> void:
	_key_label.text = label + " :"
	_value_label.text = ""
	_value_label.visible = false
	BadgeHelper.populate_badges(_badges, shelf, call_number)
