# Screen 2: Name Input with Search
extends Control

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _breadcrumb: Breadcrumb = %Breadcrumb
@onready var _search_input: LineEdit = %SearchInput
@onready var _validate_btn: Button = %ValidateBtn
@onready var _error_lbl: Label = %ErrorLabel
@onready var _candidates: VBoxContainer = %CandidatesContainer

func _ready() -> void:
	_bg.color = ThemeManager.BG

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(_screen): Mgr.pop())

	visibility_changed.connect(func():
		if visible: _update_breadcrumb()
	)

	_update_breadcrumb()

	_search_input.placeholder_text = I18n.t("name_input.placeholder")
	_search_input.text_submitted.connect(func(_t): _search())
	_search_input.call_deferred("grab_focus")

	_validate_btn.text = I18n.t("common.validate")
	_validate_btn.pressed.connect(func(): _search())

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		Mgr.pop()
		get_viewport().set_input_as_handled()

func _update_breadcrumb() -> void:
	_breadcrumb.set_path([
		{"text": GS.library_name, "screen": "class_select", "clickable": true},
		{"text": GS.current_class.get("name", ""), "screen": "", "clickable": false}
	])

func _search() -> void:
	var txt := _search_input.get_text().strip_edges()
	_error_lbl.text = ""
	_clear_candidates()

	if txt.length() < 2:
		_error_lbl.text = I18n.t("name_input.min_chars")
		return

	var result = await API.get_students(GS.current_class.get("id", 0), txt)

	if result.has("error"):
		_error_lbl.text = I18n.t("common.error_network")
		return

	var students = result.get("items", [])
	if students.is_empty():
		_error_lbl.text = I18n.t("name_input.not_found")
	elif students.size() == 1:
		_login(students[0])
	else:
		_show_candidates(students)

func _show_candidates(students: Array) -> void:
	var hint := Label.new()
	hint.text = I18n.t("name_choice.title", {"name": _search_input.get_text()})
	_candidates.add_child(hint)

	for student in students:
		var s := student as Dictionary
		var name_text := "%s %s" % [s.get("first_name", ""), s.get("last_name", "")]
		var count := int(s.get("current_loans_count", 0))
		var count_text := ""
		if count == 0:
			count_text = I18n.t("name_choice.no_books")
		elif count == 1:
			count_text = I18n.t("name_choice.books_count_one", {"count": count})
		else:
			count_text = I18n.t("name_choice.books_count_other", {"count": count})

		var btn := Button.new()
		btn.text = "%s - %s" % [name_text, count_text]
		btn.custom_minimum_size = Vector2(450, 48)
		var student_ref := s
		btn.pressed.connect(func(): _login(student_ref))
		_candidates.add_child(btn)

func _clear_candidates() -> void:
	for c in _candidates.get_children():
		c.queue_free()

func _login(student: Dictionary) -> void:
	GS.current_borrower = student
	Mgr.replace("main_menu")
