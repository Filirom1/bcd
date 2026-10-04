# Screen 3: Main Menu (Hub)
extends Control

const LOAN_CARD = preload("res://src/components/LoanCard.tscn")
const EMPTY_STATE = preload("res://src/components/EmptyState.tscn")
const CIRCULATION = preload("res://src/utils/CirculationHelper.gd")
const DATA = preload("res://src/utils/DataHelper.gd")
const ERROR_MESSAGES = preload("res://src/utils/ErrorMessages.gd")
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _breadcrumb: Breadcrumb = %Breadcrumb
@onready var _name_lbl: Label = %NameLabel
@onready var _count_lbl: Label = %CountLabel
@onready var _books_title: Label = %BooksSectionTitle
@onready var _actions_title: Label = %ActionsSectionTitle
@onready var _loans_container: VBoxContainer = %LoansContainer
@onready var _checkout_btn: Button = %CheckoutBtn
@onready var _search_btn: Button = %SearchBtn
@onready var _return_btn: Button = %ReturnBtn
@onready var _holds_btn: Button = %HoldsBtn

var _load_request_id := 0

func _ready() -> void:
	_bg.color = ThemeManager.BG

	_books_title.text = I18n.t("main_menu.my_books")
	_actions_title.text = I18n.t("main_menu.actions")

	_back_btn.text = "← " + I18n.t("common.back")
	_back_btn.pressed.connect(func():
		GS.reset_borrower()
		Mgr.reset_to("class_select")
	)

	_breadcrumb.crumb_clicked.connect(func(_screen):
		GS.reset_borrower()
		Mgr.reset_to("class_select")
	)

	_checkout_btn.text = "📖 " + I18n.t("main_menu.checkout")
	_search_btn.text = "🔍 " + I18n.t("main_menu.search")
	_return_btn.text = "✅ " + I18n.t("main_menu.return_scan")
	_holds_btn.text = "⭐ " + I18n.t("main_menu.my_holds")

	_checkout_btn.pressed.connect(func(): Mgr.push("checkout"))
	_search_btn.pressed.connect(func(): Mgr.push("search"))
	_return_btn.pressed.connect(func(): Mgr.push("return_scan"))
	_holds_btn.pressed.connect(func(): Mgr.push("my_holds"))

	_checkout_btn.focus_entered.connect(func(): _apply_focus_style(_checkout_btn))
	_checkout_btn.focus_exited.connect(func(): _remove_focus_style(_checkout_btn))
	_search_btn.focus_entered.connect(func(): _apply_focus_style(_search_btn))
	_search_btn.focus_exited.connect(func(): _remove_focus_style(_search_btn))
	_return_btn.focus_entered.connect(func(): _apply_focus_style(_return_btn))
	_return_btn.focus_exited.connect(func(): _remove_focus_style(_return_btn))
	_holds_btn.focus_entered.connect(func(): _apply_focus_style(_holds_btn))
	_holds_btn.focus_exited.connect(func(): _remove_focus_style(_holds_btn))

	_update_breadcrumb()
	_update_name()
	_update_counter()
	_load_data()
	_checkout_btn.call_deferred("grab_focus")

# Refresh the borrower data whenever the existing menu becomes visible again.
func on_enter() -> void:
	_books_title.text = I18n.t("main_menu.my_books")
	_actions_title.text = I18n.t("main_menu.actions")
	_back_btn.text = "← " + I18n.t("common.back")
	_checkout_btn.text = "📖 " + I18n.t("main_menu.checkout")
	_search_btn.text = "🔍 " + I18n.t("main_menu.search")
	_return_btn.text = "✅ " + I18n.t("main_menu.return_scan")
	_holds_btn.text = "⭐ " + I18n.t("main_menu.my_holds")
	_update_breadcrumb()
	_update_name()
	_update_counter()
	_load_data()
	_checkout_btn.call_deferred("grab_focus")

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		GS.reset_borrower()
		Mgr.reset_to("class_select")
		get_viewport().set_input_as_handled()

func _load_data() -> void:
	_load_request_id += 1
	var request_id := _load_request_id
	var generation := Mgr.navigation_generation
	var borrower_id := str(GS.current_borrower.get("borrower_id", ""))
	var loans_result = await CIRCULATION.refresh_loans(borrower_id)
	if not _is_load_current(request_id, generation, borrower_id):
		return
	if loans_result is Dictionary and not loans_result.has("error"):
		CIRCULATION.apply_loans_result(loans_result, GS.current_borrower)
		_refresh_loans()
		_update_counter()

	var holds = await API.get_holds(int(GS.current_borrower.get("id", 0)))
	if not _is_load_current(request_id, generation, borrower_id):
		return
	if holds is Array:
		GS.current_holds = holds

func _is_load_current(request_id: int, generation: int, borrower_id: String) -> bool:
	return is_inside_tree() \
		and request_id == _load_request_id \
		and Mgr.is_generation_current(generation) \
		and str(GS.current_borrower.get("borrower_id", "")) == borrower_id

func _refresh_loans() -> void:
	NODE_HELPER.clear_children(_loans_container)

	if GS.current_loans.is_empty():
		var empty_message := EMPTY_STATE.instantiate() as EmptyState
		_loans_container.add_child(empty_message)
		empty_message.setup("📚 " + I18n.t("main_menu.no_loans"))
		return

	for loan in GS.current_loans:
		if not (loan is Dictionary):
			continue
		var card := LOAN_CARD.instantiate() as LoanCard
		_loans_container.add_child(card)
		card.setup(loan)
		card.renew_clicked.connect(_renew_item)
		card.title_clicked.connect(_show_book_detail)

func _renew_item(item_id: String) -> void:
	_load_request_id += 1
	var request_id := _load_request_id
	var generation := Mgr.navigation_generation
	var borrower_id := str(GS.current_borrower.get("borrower_id", ""))
	var result = await CIRCULATION.renew_book(item_id, borrower_id)
	if not _is_load_current(request_id, generation, borrower_id):
		return
	if not (result is Dictionary) or result.has("error"):
		Mgr.notify(ERROR_MESSAGES.message(result, ERROR_MESSAGES.RENEW), "error")
		return
	var renewed := DATA.array(result, "renewed")
	if renewed.is_empty():
		Mgr.notify(I18n.t("main_menu.renew_no_items"), "error")
		return
	var new_date := DATA.text(renewed[0], "new_due_date") if renewed[0] is Dictionary else ""
	Mgr.notify(I18n.t("main_menu.renew_success", {"date": new_date}), "success")
	var loans_result = await CIRCULATION.refresh_loans(borrower_id)
	if not _is_load_current(request_id, generation, borrower_id):
		return
	if loans_result is Dictionary and not loans_result.has("error"):
		CIRCULATION.apply_loans_result(loans_result, GS.current_borrower)
		_refresh_loans()
		_update_counter()
		_checkout_btn.call_deferred("grab_focus")
func _show_book_detail(loan: Dictionary) -> void:
	var book_data := loan.duplicate()
	book_data["id"] = loan.get("bibliographic_record_id", 0)
	GS.set_nav_param("book_data", book_data)
	Mgr.push("book_detail")

func _update_breadcrumb() -> void:
	_breadcrumb.set_path(CIRCULATION.borrower_breadcrumb(
		"%s %s" % [DATA.text(GS.current_borrower, "first_name"), DATA.text(GS.current_borrower, "last_name")],
		false
	))

func _update_name() -> void:
	_name_lbl.text = "%s %s" % [DATA.text(GS.current_borrower, "first_name"), DATA.text(GS.current_borrower, "last_name")]

func _update_counter() -> void:
	CIRCULATION.update_counter(_count_lbl, GS.current_borrower)

func _apply_focus_style(btn: Button) -> void:
	ThemeManager.apply_focus_style(btn)

func _remove_focus_style(btn: Button) -> void:
	ThemeManager.remove_focus_style(btn)
