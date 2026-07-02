# Screen 3: Main Menu (Hub)
extends Control

const LOAN_CARD = preload("res://src/components/LoanCard.tscn")

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

func _ready() -> void:
	_bg.color = ThemeManager.BG

	_books_title.text = I18n.t("main_menu.my_books")

	_back_btn.text = "← " + I18n.t("common.back")
	_back_btn.pressed.connect(func():
		GS.reset_borrower()
		Mgr.replace("class_select")
	)

	_breadcrumb.crumb_clicked.connect(func(_screen):
		GS.reset_borrower()
		Mgr.replace("class_select")
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

	visibility_changed.connect(func():
		if visible:
			_update_breadcrumb()
			_update_name()
			_update_counter()
			_refresh_loans()
			_checkout_btn.call_deferred("grab_focus")
	)

	_update_breadcrumb()
	_update_name()
	_update_counter()
	_load_data()
	_checkout_btn.call_deferred("grab_focus")

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		GS.reset_borrower()
		Mgr.replace("class_select")
		get_viewport().set_input_as_handled()

func _load_data() -> void:
	var loans_result = await API.get_current_loans(GS.current_borrower.get("borrower_id", ""))
	if not loans_result.has("error"):
		GS.current_loans = loans_result.get("loans", [])
		GS.current_borrower.current_loans_count = GS.current_loans.size()
		_refresh_loans()
		_update_counter()
	var holds = await API.get_holds(GS.current_borrower.get("id", 0))
	GS.current_holds = holds

func _refresh_loans() -> void:
	for c in _loans_container.get_children():
		c.queue_free()

	if GS.current_loans.is_empty():
		var lbl := Label.new()
		lbl.text = "📚 " + I18n.t("main_menu.no_loans")
		lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_loans_container.add_child(lbl)
		return

	for loan in GS.current_loans:
		var card := LOAN_CARD.instantiate() as LoanCard
		_loans_container.add_child(card)
		card.setup(loan as Dictionary)
		card.return_clicked.connect(_return_item)
		card.renew_clicked.connect(_renew_item)
		card.title_clicked.connect(_show_book_cover)

func _return_item(item_id: String) -> void:
	var result = await API.return_items([item_id])
	if result.has("error"):
		Mgr.notify(I18n.t("return.error_not_on_loan"), "error")
	else:
		var items = result.get("items", [])
		var title: String = ""
		if items.size() > 0:
			title = items[0].get("display_title", items[0].get("title", ""))

		if title.is_empty():
			Mgr.notify(I18n.t("return.success"), "success")
		else:
			Mgr.notify(I18n.t("return.success_with_title", {"title": title}), "success")

		if items.size() > 0:
			var hold_ready = items[0].get("hold_ready", null)
			if hold_ready != null and hold_ready is Dictionary:
				GS.current_class["_temp_hold_ready"] = {
					"title": items[0].get("display_title", items[0].get("title", "")),
					"borrower_name": hold_ready.get("borrower_name", ""),
					"class_name": hold_ready.get("class_name", ""),
					"borrower_id": hold_ready.get("borrower_id", "")
				}
				Mgr.push("hold_ready")

		var loans_result = await API.get_current_loans(GS.current_borrower.get("borrower_id", ""))
		if not loans_result.has("error"):
			GS.current_loans = loans_result.get("loans", [])
			GS.current_borrower.current_loans_count = GS.current_loans.size()
			_refresh_loans()
			_update_counter()
			_checkout_btn.call_deferred("grab_focus")

func _renew_item(item_id: String) -> void:
	var result = await API.renew_items(GS.current_borrower.get("borrower_id", ""), [item_id])
	if result.has("error"):
		var code: String = result.get("detail", {}).get("code", "")
		match code:
			"no_renewable_items":
				Mgr.notify(I18n.t("main_menu.renew_no_items"), "error")
			_:
				Mgr.notify(I18n.t("common.error_unknown"), "error")
		return
	var renewed = result.get("renewed", [])
	if renewed.is_empty():
		Mgr.notify(I18n.t("main_menu.renew_no_items"), "error")
		return
	var new_date: String = renewed[0].get("new_due_date", "")
	Mgr.notify(I18n.t("main_menu.renew_success", {"date": new_date}), "success")
	var loans_result = await API.get_current_loans(GS.current_borrower.get("borrower_id", ""))
	if not loans_result.has("error"):
		GS.current_loans = loans_result.get("loans", [])
		GS.current_borrower.current_loans_count = GS.current_loans.size()
		_refresh_loans()
		_update_counter()
		_checkout_btn.call_deferred("grab_focus")
func _show_book_cover(loan: Dictionary) -> void:
	var book_data := loan.duplicate()
	book_data["id"] = loan.get("bibliographic_record_id", 0)
	GS.current_class["_temp_book_data"] = book_data
	Mgr.push("book_detail")

func _update_breadcrumb() -> void:
	_breadcrumb.set_path([
		{"text": GS.library_name, "screen": "class_select", "clickable": true},
		{"text": GS.current_class.get("name", ""), "screen": "class_select", "clickable": true},
		{"text": "%s %s" % [GS.current_borrower.get("first_name", ""), GS.current_borrower.get("last_name", "")], "screen": "", "clickable": false}
	])

func _update_name() -> void:
	_name_lbl.text = "%s %s" % [GS.current_borrower.get("first_name", ""), GS.current_borrower.get("last_name", "")]

func _update_counter() -> void:
	var current := int(GS.current_borrower.get("current_loans_count", 0))
	var limit := int(GS.current_borrower.get("loan_limit", 3))
	var warning_limit := int(GS.current_borrower.get("loan_limit_warning", 0))
	
	_count_lbl.text = I18n.t("main_menu.books_count", {"current": current, "limit": limit})
	
	if current >= limit:
		_count_lbl.add_theme_color_override("font_color", ThemeManager.ERROR)
	elif warning_limit > 0 and current >= warning_limit:
		_count_lbl.add_theme_color_override("font_color", ThemeManager.WARNING)
	else:
		_count_lbl.remove_theme_color_override("font_color")

func _apply_focus_style(btn: Button) -> void:
	btn.add_theme_stylebox_override("normal", btn.get_theme_stylebox("hover"))
	btn.add_theme_color_override("font_color", ThemeManager.TEXT)

func _remove_focus_style(btn: Button) -> void:
	btn.remove_theme_stylebox_override("normal")
	btn.remove_theme_color_override("font_color")