# Class Button Component
class_name ClassButton
extends Button

signal class_selected(cls: Dictionary)

@onready var _name_lbl: Label = %ClassNameLabel
@onready var _teacher_lbl: Label = %TeacherLabel

var _cls_data: Dictionary

func _ready() -> void:
	focus_entered.connect(func():
		ThemeManager.apply_focus_style(self)
	)
	focus_exited.connect(func():
		ThemeManager.remove_focus_style(self)
	)

func setup(cls: Dictionary) -> void:
	_cls_data = cls
	_name_lbl.text = cls.get("name") if cls.get("name") is String else ""
	var teacher: String = cls.get("homeroom_teacher") if cls.get("homeroom_teacher") is String else ""
	_teacher_lbl.text = "👨‍🏫 " + teacher if teacher else ""
	_teacher_lbl.visible = not teacher.is_empty()

func _pressed() -> void:
	class_selected.emit(_cls_data)
