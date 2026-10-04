# Screen 7: My Holds (Reservations)
extends Control

const HOLD_CARD = preload("res://src/components/HoldCard.tscn")
const EMPTY_STATE = preload("res://src/components/EmptyState.tscn")
const CIRCULATION = preload("res://src/utils/CirculationHelper.gd")
const DATA = preload("res://src/utils/DataHelper.gd")
const ERROR_MESSAGES = preload("res://src/utils/ErrorMessages.gd")
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _breadcrumb: Breadcrumb = %Breadcrumb
@onready var _title_lbl: Label = %TitleLabel
@onready var _name_lbl: Label = %NameLabel
@onready var _holds_container: VBoxContainer = %HoldsContainer

var _load_request_id := 0
var _last_load_result: Variant = {}

func _ready() -> void:
	_bg.color = ThemeManager.BG

	_title_lbl.text = I18n.t("main_menu.my_holds")
	_back_btn.text = "← " + I18n.t("common.back")

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(screen):
		if screen == "class_select": GS.reset_borrower()
		Mgr.replace(screen)
	)

	_back_btn.focus_entered.connect(func():
		ThemeManager.apply_focus_style(_back_btn)
	)
	_back_btn.focus_exited.connect(func():
		ThemeManager.remove_focus_style(_back_btn)
	)

	_update_breadcrumb()
	_update_name()
	_load_holds()
	_back_btn.call_deferred("grab_focus")

func on_enter() -> void:
	_title_lbl.text = I18n.t("main_menu.my_holds")
	_back_btn.text = "← " + I18n.t("common.back")
	_update_breadcrumb()
	_update_name()
	_load_holds()
	_back_btn.call_deferred("grab_focus")

func _input(event: InputEvent) -> void:
	if not visible:
		return
	if not (event is InputEventKey and event.pressed and not event.echo):
		return
	if not _back_btn.has_focus():
		return
	if event.keycode in [KEY_DOWN, KEY_UP, KEY_LEFT, KEY_RIGHT]:
		var cards := _holds_container.get_children()
		if not cards.is_empty() and cards[0] is HoldCard:
			(cards[0] as HoldCard).grab_first_focus()
			accept_event()

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		Mgr.pop()
		get_viewport().set_input_as_handled()

func _load_holds(show_error: bool = true) -> bool:
	_load_request_id += 1
	var request_id := _load_request_id
	var generation := Mgr.navigation_generation
	var borrower_id := str(GS.current_borrower.get("borrower_id", ""))
	var holds = await API.get_holds(int(GS.current_borrower.get("id", 0)))
	if not _is_load_current(request_id, generation, borrower_id):
		return false
	if holds is Array:
		_last_load_result = {}
		GS.current_holds = holds
		_refresh_holds(false)
		return true
	_last_load_result = holds
	if show_error:
		_refresh_holds(true)
	return false

func _is_load_current(request_id: int, generation: int, borrower_id: String) -> bool:
	return is_inside_tree() \
		and request_id == _load_request_id \
		and Mgr.is_generation_current(generation) \
		and str(GS.current_borrower.get("borrower_id", "")) == borrower_id

func _refresh_holds(load_error: bool = false) -> void:
	NODE_HELPER.clear_children(_holds_container)

	if load_error:
		var error_message := EMPTY_STATE.instantiate() as EmptyState
		_holds_container.add_child(error_message)
		error_message.setup(ERROR_MESSAGES.message(_last_load_result, ERROR_MESSAGES.COMMON))
		return

	if GS.current_holds.is_empty():
		var empty_message := EMPTY_STATE.instantiate() as EmptyState
		_holds_container.add_child(empty_message)
		empty_message.setup(I18n.t("main_menu.no_holds"))
		return

	for hold in GS.current_holds:
		if not (hold is Dictionary):
			continue
		var card := HOLD_CARD.instantiate() as HoldCard
		_holds_container.add_child(card)
		card.setup(hold)
		card.cancel_clicked.connect(_cancel_hold)

func _update_breadcrumb() -> void:
	_breadcrumb.set_path(CIRCULATION.borrower_breadcrumb(I18n.t("main_menu.my_holds")))

func _update_name() -> void:
	_name_lbl.text = "%s %s" % [DATA.text(GS.current_borrower, "first_name"), DATA.text(GS.current_borrower, "last_name")]

func _cancel_hold(hold_id: int) -> void:
	var generation := Mgr.navigation_generation
	var hold_title := ""
	for hold in GS.current_holds:
		if hold is Dictionary and int(hold.get("id", 0)) == hold_id:
			hold_title = DATA.text(hold, "title")
			break

	var result = await API.cancel_hold(hold_id)
	if not is_inside_tree() or not Mgr.is_generation_current(generation):
		return
	if result is Dictionary and result.has("error"):
		Mgr.notify(ERROR_MESSAGES.message(result, ERROR_MESSAGES.HOLD), "error")
		return

	if hold_title.is_empty():
		Mgr.notify(I18n.t("hold.cancelled"), "warning")
	else:
		Mgr.notify(I18n.t("hold.cancelled_with_title", {"title": hold_title}), "warning")

	# The cancellation succeeded. Remove the hold locally before refreshing so a
	# transient refresh failure cannot report the successful operation as failed.
	var remaining: Array = []
	for hold in GS.current_holds:
		if not (hold is Dictionary) or int(hold.get("id", 0)) != hold_id:
			remaining.append(hold)
	GS.current_holds = remaining
	_refresh_holds(false)
	if not await _load_holds(false):
		if is_inside_tree() and Mgr.is_generation_current(generation):
			Mgr.notify(I18n.t("common.refresh_failed"), "warning")
	_back_btn.call_deferred("grab_focus")
