# Screen 1: Class Selection
extends Control

const CLASS_BTN = preload("res://src/components/ClassButton.tscn")
const EMPTY_STATE = preload("res://src/components/EmptyState.tscn")
const CIRCULATION = preload("res://src/utils/CirculationHelper.gd")
const ERROR_MESSAGES = preload("res://src/utils/ErrorMessages.gd")

@onready var _bg: ColorRect = %Background
@onready var _server_btn: Button = %ServerBtn
@onready var _settings_btn: Button = %SettingsBtn
@onready var _fr_btn: Button = %FrBtn
@onready var _en_btn: Button = %EnBtn
@onready var _title_lbl: Label = %TitleLabel
@onready var _scan_input: LineEdit = %ScanInput
@onready var _classes_grid: GridContainer = %ClassesGrid

var _classes_request_id := 0
var _scan_busy := false

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_title_lbl.text = I18n.t("class_select.title")
	_update_server_button()

	_server_btn.pressed.connect(func(): Mgr.replace("server_discovery"))
	_settings_btn.pressed.connect(func(): Mgr.push("settings"))

	_fr_btn.pressed.connect(func():
		I18n.set_locale("fr")
		_refresh_ui()
	)
	_en_btn.pressed.connect(func():
		I18n.set_locale("en")
		_refresh_ui()
	)

	_scan_input.keep_editing_on_text_submit = true
	_scan_input.placeholder_text = I18n.t("class_select.scan_placeholder")
	_scan_input.text_submitted.connect(func(t): _handle_scan(t))
	_scan_input.call_deferred("grab_focus")
	_load_classes()

# Called by Mgr when this screen is shown again after a student logout or a
# server/settings change. The first entry is initialized by _ready().
func on_enter() -> void:
	_update_server_button()
	_refresh_ui()
	_scan_input.call_deferred("grab_focus")

func _update_server_button() -> void:
	var lib_name: String
	if not GS.library_name.is_empty():
		lib_name = GS.library_name
	elif GS.base_url.contains("127.0.0.1") or GS.base_url.contains("localhost"):
		lib_name = I18n.t("server_discovery.localhost_default")
	else:
		lib_name = I18n.t("common.home")
	_server_btn.text = lib_name

func _handle_scan(text: String) -> void:
	_scan_input.clear()
	_scan_input.call_deferred("grab_focus")
	if _scan_busy:
		return

	var parsed := BarcodeHelper.parse_class_scan(text, GS.settings)
	var kind: String = parsed.get("kind", "unknown")
	var id: String = parsed.get("id", "")
	if id.is_empty():
		if not BarcodeHelper.clean(text).is_empty():
			Mgr.notify(I18n.t("common.scan_not_recognized"), "error")
		return

	if kind == "borrower":
		_login_by_card(id)
	elif kind == "item":
		_quick_return(id)

func _quick_return(item_id: String) -> void:
	if item_id.is_empty() or _scan_busy:
		return
	_scan_busy = true
	var generation := Mgr.navigation_generation
	var result = await CIRCULATION.return_book(item_id)
	if not is_inside_tree() or not Mgr.is_generation_current(generation):
		_scan_busy = false
		return

	if result is Dictionary and result.has("error"):
		Mgr.notify(ERROR_MESSAGES.message(result, ERROR_MESSAGES.RETURN), "error")
		ThemeManager.animate_error_shake(_scan_input)
		_scan_busy = false
		return

	var items = result.get("items", []) if result is Dictionary else []
	var title: String = ""
	if items.size() > 0 and items[0] is Dictionary:
		title = CIRCULATION.display_title(items[0])

	if title.is_empty():
		Mgr.notify(I18n.t("return.success"), "success")
	else:
		Mgr.notify(I18n.t("return.success_with_title", {"title": title}), "success")

	if items.size() > 0 and items[0] is Dictionary:
		var hold_ready := CIRCULATION.hold_ready_payload(items[0])
		if CIRCULATION.present_hold_ready(hold_ready):
			_scan_busy = false
			return

	ThemeManager.animate_success_flash(_scan_input)
	_scan_busy = false
	_scan_input.call_deferred("grab_focus")

func _login_by_card(card_id: String) -> void:
	if card_id.is_empty() or _scan_busy:
		return
	_scan_busy = true
	var generation := Mgr.navigation_generation
	var result = await API.get_borrower(card_id)
	if not is_inside_tree() or not Mgr.is_generation_current(generation):
		_scan_busy = false
		return

	if not (result is Dictionary) or result.has("error"):
		var fallback := "name_input.not_found"
		Mgr.notify(ERROR_MESSAGES.message(result, ERROR_MESSAGES.BORROWER, fallback), "error")
		ThemeManager.animate_error_shake(_scan_input)
		_scan_busy = false
		_scan_input.call_deferred("grab_focus")
		return

	GS.current_class = {
		"id": result.get("class_id", 0),
		"name": result.get("class_name", ""),
		"homeroom_teacher": result.get("homeroom_teacher", "")
	}
	GS.current_borrower = result
	_scan_busy = false
	Mgr.push("main_menu")

func _clear_classes() -> void:
	for child in _classes_grid.get_children():
		_classes_grid.remove_child(child)
		child.queue_free()

func _load_classes() -> void:
	_classes_request_id += 1
	var request_id := _classes_request_id
	var generation := Mgr.navigation_generation
	_clear_classes()
	var classes = await API.get_classes()
	if not is_inside_tree() or request_id != _classes_request_id \
			or not Mgr.is_generation_current(generation):
		return

	if classes is Dictionary and classes.has("error"):
		var error_message := EMPTY_STATE.instantiate() as EmptyState
		_classes_grid.add_child(error_message)
		error_message.setup(ERROR_MESSAGES.message(classes, ERROR_MESSAGES.COMMON))
		return

	if not (classes is Array) or classes.is_empty():
		var empty_message := EMPTY_STATE.instantiate() as EmptyState
		_classes_grid.add_child(empty_message)
		empty_message.setup(I18n.t("class_select.no_classes"))
		return

	classes.sort_custom(func(a, b):
		var age_a = a.get("average_age", null)
		var age_b = b.get("average_age", null)
		if age_a == null and age_b == null:
			return a.get("name", "") < b.get("name", "")
		if age_a == null:
			return false
		if age_b == null:
			return true
		if age_a != age_b:
			return age_a < age_b
		return a.get("name", "") < b.get("name", "")
	)

	for cls in classes:
		var btn := CLASS_BTN.instantiate() as ClassButton
		_classes_grid.add_child(btn)
		btn.setup(cls as Dictionary)
		btn.class_selected.connect(_select_class)

func _select_class(cls: Dictionary) -> void:
	GS.current_class = cls
	Mgr.push("name_input")

func _input(event: InputEvent) -> void:
	if not visible:
		return
	if not (event is InputEventKey and event.pressed and not event.echo):
		return
	if _scan_input.has_focus():
		if event.keycode in [KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT]:
			var buttons := _classes_grid.get_children()
			if not buttons.is_empty():
				buttons[0].grab_focus()
				accept_event()
	elif event.keycode == KEY_ESCAPE:
		_scan_input.grab_focus()
		accept_event()

func _refresh_ui() -> void:
	_title_lbl.text = I18n.t("class_select.title")
	_scan_input.placeholder_text = I18n.t("class_select.scan_placeholder")
	_update_server_button()
	_load_classes()
