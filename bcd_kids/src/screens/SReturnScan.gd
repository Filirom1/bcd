# Screen 5: Return by Scan
extends Control

const EMPTY_STATE = preload("res://src/components/EmptyState.tscn")
const HISTORY_ENTRY = preload("res://src/components/HistoryEntry.tscn")
const CIRCULATION = preload("res://src/utils/CirculationHelper.gd")
const DATA = preload("res://src/utils/DataHelper.gd")
const ERROR_MESSAGES = preload("res://src/utils/ErrorMessages.gd")
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _breadcrumb: Breadcrumb = %Breadcrumb
@onready var _title_lbl: Label = %TitleLabel
@onready var _input_lbl: Label = %InputLabel
@onready var _barcode_input: LineEdit = %BarcodeInput
@onready var _error_lbl: Label = %ErrorLabel
@onready var _validate_btn: Button = %ValidateBtn
@onready var _history_title: Label = %HistoryTitle
@onready var _history: VBoxContainer = %HistoryContainer

var _busy := false

func _ready() -> void:
	_bg.color = ThemeManager.BG

	_title_lbl.text = I18n.t("return.title")
	_input_lbl.text = I18n.t("return.label")
	_barcode_input.placeholder_text = I18n.t("common.barcode_placeholder")
	_history_title.text = I18n.t("return.returned_today")
	_back_btn.text = "← " + I18n.t("common.back")
	_validate_btn.text = "✓ " + I18n.t("common.validate")

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(screen):
		if screen == "class_select": GS.reset_borrower()
		Mgr.replace(screen)
	)

	_barcode_input.keep_editing_on_text_submit = true
	_barcode_input.text_submitted.connect(func(_t): _do_return())
	_validate_btn.pressed.connect(func(): _do_return())
	_barcode_input.call_deferred("grab_focus")
	_update_breadcrumb()

	var placeholder := EMPTY_STATE.instantiate() as EmptyState
	_history.add_child(placeholder)
	placeholder.setup(I18n.t("return.scan_books_placeholder"))

# Called when returning to this screen from another stack entry.
func on_enter() -> void:
	_title_lbl.text = I18n.t("return.title")
	_input_lbl.text = I18n.t("return.label")
	_barcode_input.placeholder_text = I18n.t("common.barcode_placeholder")
	_history_title.text = I18n.t("return.returned_today")
	_back_btn.text = "← " + I18n.t("common.back")
	_validate_btn.text = "✓ " + I18n.t("common.validate")
	_update_breadcrumb()
	_barcode_input.call_deferred("grab_focus")

func _do_return() -> void:
	if _busy:
		return
	_busy = true
	var generation := Mgr.navigation_generation
	var text := _barcode_input.get_text().strip_edges().replace(" ", "")
	_error_lbl.text = ""
	_barcode_input.clear()
	_barcode_input.grab_focus()

	if text.is_empty():
		_busy = false
		return

	var item_id := BarcodeHelper.item_id(text, GS.settings)
	if item_id.length() < 1:
		_error_lbl.text = I18n.t("return.error_not_found")
		ThemeManager.animate_error_shake(_barcode_input)
		_busy = false
		return

	var result = await CIRCULATION.return_book(item_id)
	if not is_inside_tree() or not Mgr.is_generation_current(generation):
		_busy = false
		return

	_barcode_input.grab_focus()

	if result is Dictionary and result.has("error"):
		_handle_error(result)
		ThemeManager.animate_error_shake(_barcode_input)
		_busy = false
		return
	else:
		var items := DATA.array(result, "items")
		var pending_hold_ready: Dictionary = {}
		if items.size() > 0 and items[0] is Dictionary:
			var item := items[0] as Dictionary
			var was_overdue := DATA.boolean(item, "was_overdue")
			var days_overdue := DATA.integer(item, "days_overdue")
			var borrower_name := DATA.text(item, "borrower_name")
			var title: String = CIRCULATION.display_title(item)
			var shelf := DATA.text(item, "shelf_location").strip_edges()
			var call_num := DATA.text(item, "call_number").strip_edges()
			_add_to_history(title, borrower_name, was_overdue, days_overdue, shelf, call_num)

			if title.is_empty():
				Mgr.notify(I18n.t("return.success"), "success")
			else:
				Mgr.notify(I18n.t("return.success_with_title", {"title": title}), "success")

			pending_hold_ready = CIRCULATION.hold_ready_payload(item)

			ThemeManager.animate_success_flash(_barcode_input)
			var loans_result = await CIRCULATION.refresh_loans(GS.current_borrower.get("borrower_id", ""))
			if is_inside_tree() and Mgr.is_generation_current(generation) \
					and loans_result is Dictionary and not loans_result.has("error"):
				CIRCULATION.apply_loans_result(loans_result, GS.current_borrower)
			if not is_inside_tree() or not Mgr.is_generation_current(generation):
				_busy = false
				return
			_barcode_input.grab_focus()
		if CIRCULATION.present_hold_ready(pending_hold_ready):
			_busy = false
			return
	_busy = false

func _handle_error(result: Dictionary) -> void:
	_error_lbl.text = ERROR_MESSAGES.message(result, ERROR_MESSAGES.RETURN)

func _update_breadcrumb() -> void:
	_breadcrumb.set_path(CIRCULATION.borrower_breadcrumb(I18n.t("return.title")))

func _add_to_history(
	title: String,
	borrower_name: String,
	was_late: bool,
	days_overdue: int,
	shelf: String,
	call_num: String
) -> void:
	if _history.get_child_count() == 1 and _history.get_child(0) is EmptyState:
		NODE_HELPER.dispose(_history.get_child(0))

	var entry := HISTORY_ENTRY.instantiate() as HistoryEntry
	_history.add_child(entry)
	entry.setup(title, borrower_name, was_late, days_overdue, shelf, call_num)

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		var viewport := get_viewport()
		if viewport != null:
			viewport.set_input_as_handled()
		Mgr.pop()
