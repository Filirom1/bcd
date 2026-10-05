# Screen 4: Checkout (Borrow books)
extends Control

const EMPTY_STATE = preload("res://src/components/EmptyState.tscn")
const LOAN_SUMMARY = preload("res://src/components/LoanSummary.tscn")
const CIRCULATION = preload("res://src/utils/CirculationHelper.gd")
const DATA = preload("res://src/utils/DataHelper.gd")
const ERROR_MESSAGES = preload("res://src/utils/ErrorMessages.gd")
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _breadcrumb: Breadcrumb = %Breadcrumb
@onready var _title_lbl: Label = %TitleLabel
@onready var _count_lbl: Label = %CountLabel
@onready var _input_lbl: Label = %InputLabel
@onready var _barcode_input: LineEdit = %BarcodeInput
@onready var _error_lbl: Label = %ErrorLabel
@onready var _loans_list: VBoxContainer = %LoansList
@onready var _validate_btn: Button = %ValidateBtn

var _busy := false

func _ready() -> void:
	_bg.color = ThemeManager.BG

	_title_lbl.text = I18n.t("checkout.title")
	_input_lbl.text = I18n.t("checkout.label")
	_barcode_input.placeholder_text = I18n.t("common.barcode_placeholder")
	_back_btn.text = "← " + I18n.t("common.back")
	_validate_btn.text = "✓ " + I18n.t("common.validate")

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(screen):
		if screen == "class_select": GS.reset_borrower()
		Mgr.replace(screen)
	)

	_barcode_input.keep_editing_on_text_submit = true
	_barcode_input.text_submitted.connect(func(_t): _do_checkout())
	_validate_btn.pressed.connect(func(): _do_checkout())
	_barcode_input.call_deferred("grab_focus")

	_update_breadcrumb()
	_update_counter()
	_refresh_list()

# Called when returning to this screen from another stack entry.
func on_enter() -> void:
	_title_lbl.text = I18n.t("checkout.title")
	_input_lbl.text = I18n.t("checkout.label")
	_barcode_input.placeholder_text = I18n.t("common.barcode_placeholder")
	_back_btn.text = "← " + I18n.t("common.back")
	_validate_btn.text = "✓ " + I18n.t("common.validate")
	_update_breadcrumb()
	_update_counter()
	_refresh_list()
	_barcode_input.call_deferred("grab_focus")

func _do_checkout() -> void:
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
		_error_lbl.text = I18n.t("checkout.error_not_found")
		ThemeManager.animate_error_shake(_barcode_input)
		_busy = false
		return

	var result = await API.checkout(GS.current_borrower.get("borrower_id", ""), [item_id])
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
		var transactions := DATA.array(result, "transactions")
		var title: String = ""
		if transactions.size() > 0 and transactions[0] is Dictionary:
			title = DATA.display_title(transactions[0])

		# Refresh loans count first
		var loans_result = await CIRCULATION.refresh_loans(GS.current_borrower.get("borrower_id", ""))
		if not is_inside_tree() or not Mgr.is_generation_current(generation):
			_busy = false
			return
		if loans_result is Dictionary and not loans_result.has("error"):
			CIRCULATION.apply_loans_result(loans_result, GS.current_borrower)

		var warning_limit := DATA.integer(GS.current_borrower, "loan_limit_warning")
		var current_count := DATA.integer(GS.current_borrower, "current_loans_count")
		var is_warning := warning_limit > 0 and current_count >= warning_limit

		if is_warning:
			if title.is_empty():
				Mgr.notify(I18n.t("checkout.success_warning"), "warning")
			else:
				Mgr.notify(I18n.t("checkout.success_warning_with_title", {"title": title}), "warning")
		else:
			if title.is_empty():
				Mgr.notify(I18n.t("checkout.success"), "success")
			else:
				Mgr.notify(I18n.t("checkout.success_with_title", {"title": title}), "success")

		ThemeManager.animate_success_flash(_barcode_input)
		_refresh_list()
		_update_counter()
		_barcode_input.grab_focus()
	_busy = false

func _handle_error(result: Dictionary) -> void:
	_error_lbl.text = ERROR_MESSAGES.message(result, ERROR_MESSAGES.CHECKOUT)

func _update_breadcrumb() -> void:
	_breadcrumb.set_path(CIRCULATION.borrower_breadcrumb(I18n.t("checkout.title")))

func _update_counter() -> void:
	CIRCULATION.update_counter(_count_lbl, GS.current_borrower)

func _refresh_list() -> void:
	NODE_HELPER.clear_children(_loans_list)
	if GS.current_loans.is_empty():
		var empty_message := EMPTY_STATE.instantiate() as EmptyState
		_loans_list.add_child(empty_message)
		empty_message.setup(I18n.t("checkout.no_loans"))
		return
	for loan in GS.current_loans:
		if not (loan is Dictionary):
			continue
		var summary := LOAN_SUMMARY.instantiate() as LoanSummary
		_loans_list.add_child(summary)
		summary.setup(loan)

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		var viewport := get_viewport()
		if viewport != null:
			viewport.set_input_as_handled()
		Mgr.pop()
