# Screen 2: Name Input with Search
extends Control

const CANDIDATE_BUTTON = preload("res://src/components/CandidateButton.tscn")
const EMPTY_STATE = preload("res://src/components/EmptyState.tscn")
const ERROR_MESSAGES = preload("res://src/utils/ErrorMessages.gd")
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _title_lbl: Label = get_node("MainMargin/Root/FormCenter/Form/TitleLabel")
@onready var _breadcrumb: Breadcrumb = %Breadcrumb
@onready var _search_input: LineEdit = %SearchInput
@onready var _validate_btn: Button = %ValidateBtn
@onready var _error_lbl: Label = %ErrorLabel
@onready var _candidates: VBoxContainer = %CandidatesContainer

var _search_request_id := 0

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_title_lbl.text = I18n.t("name_input.title")
	_back_btn.text = "← " + I18n.t("common.back")
	_validate_btn.text = I18n.t("common.validate")

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(_screen): Mgr.pop())

	_update_breadcrumb()

	_search_input.placeholder_text = I18n.t("name_input.placeholder")
	_search_input.text_submitted.connect(func(_t): _search())
	_search_input.call_deferred("grab_focus")

	_validate_btn.text = I18n.t("common.validate")
	_validate_btn.pressed.connect(func(): _search())

func on_enter() -> void:
	_title_lbl.text = I18n.t("name_input.title")
	_back_btn.text = "← " + I18n.t("common.back")
	_validate_btn.text = I18n.t("common.validate")
	_search_input.placeholder_text = I18n.t("name_input.placeholder")
	_update_breadcrumb()
	_search_input.call_deferred("grab_focus")

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
	_search_request_id += 1
	var request_id := _search_request_id
	var generation := Mgr.navigation_generation
	var txt := _search_input.get_text().strip_edges()
	_error_lbl.text = ""
	_clear_candidates()

	if txt.length() < 2:
		_error_lbl.text = I18n.t("name_input.min_chars")
		return

	var result = await API.get_students(GS.current_class.get("id", 0), txt)
	if not is_inside_tree() or request_id != _search_request_id \
			or not Mgr.is_generation_current(generation):
		return

	if not (result is Dictionary) or result.has("error"):
		_error_lbl.text = ERROR_MESSAGES.message(result, ERROR_MESSAGES.BORROWER)
		return

	var students = result.get("items", [])
	if not (students is Array):
		_error_lbl.text = I18n.t("common.error_unknown")
		return
	if students.is_empty():
		_error_lbl.text = I18n.t("name_input.not_found")
	elif students.size() == 1:
		_login(students[0])
	else:
		_show_candidates(students)

func _show_candidates(students: Array) -> void:
	var hint := EMPTY_STATE.instantiate() as EmptyState
	_candidates.add_child(hint)
	hint.setup(I18n.t("name_choice.title", {"name": _search_input.get_text()}), HORIZONTAL_ALIGNMENT_LEFT)

	for student in students:
		if not (student is Dictionary):
			continue
		var button := CANDIDATE_BUTTON.instantiate() as CandidateButton
		_candidates.add_child(button)
		button.setup(student)
		button.candidate_selected.connect(_login)

func _clear_candidates() -> void:
	NODE_HELPER.clear_children(_candidates)

func _login(student: Dictionary) -> void:
	GS.current_borrower = student
	Mgr.replace("main_menu")
