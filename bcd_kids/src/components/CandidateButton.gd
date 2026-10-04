# Candidate selection button used when several students match a name.
class_name CandidateButton
extends Button

const DATA = preload("res://src/utils/DataHelper.gd")

signal candidate_selected(student: Dictionary)

var _student: Dictionary = {}

func _ready() -> void:
	pressed.connect(_on_pressed)
	focus_entered.connect(func(): ThemeManager.apply_focus_style(self))
	focus_exited.connect(func(): ThemeManager.remove_focus_style(self))

func setup(student: Dictionary) -> void:
	_student = student
	var name_text := "%s %s" % [DATA.text(student, "first_name"), DATA.text(student, "last_name")]
	var count := DATA.integer(student, "current_loans_count")
	var count_key := "name_choice.no_books"
	if count == 1:
		count_key = "name_choice.books_count_one"
	elif count > 1:
		count_key = "name_choice.books_count_other"
	var count_text := I18n.t(count_key, {"count": count})
	text = I18n.t("name_choice.candidate", {"name": name_text, "count": count_text})

func _on_pressed() -> void:
	candidate_selected.emit(_student)
