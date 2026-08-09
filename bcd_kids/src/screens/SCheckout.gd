# Screen 4: Checkout (Borrow books)
extends Control

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

func _ready() -> void:
	_bg.color = ThemeManager.BG

	_title_lbl.text = I18n.t("checkout.title")
	_input_lbl.text = I18n.t("checkout.label")

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(screen):
		if screen == "class_select": GS.reset_borrower()
		Mgr.replace(screen)
	)

	_barcode_input.keep_editing_on_text_submit = true
	_barcode_input.text_submitted.connect(func(_t): _do_checkout())
	_validate_btn.pressed.connect(func(): _do_checkout())
	_barcode_input.call_deferred("grab_focus")
	visibility_changed.connect(func():
		if visible:
			_update_breadcrumb()
			_update_counter()
			_refresh_list()
			_barcode_input.call_deferred("grab_focus")
	)

	_update_breadcrumb()
	_update_counter()
	_refresh_list()

func _do_checkout() -> void:
	var text := _barcode_input.get_text().strip_edges()
	_error_lbl.text = ""
	_barcode_input.clear()
	_barcode_input.grab_focus()

	if text.is_empty():
		return

	var item_id := text
	var prefix: String = GS.settings.get("item_barcode_prefix", ".")
	if not prefix.is_empty() and text.begins_with(prefix):
		item_id = text.substr(prefix.length())

	if item_id.length() < 1:
		_error_lbl.text = I18n.t("checkout.error_not_found")
		ThemeManager.animate_error_shake(_barcode_input)
		return

	var result = await API.checkout(GS.current_borrower.get("borrower_id", ""), [item_id])

	_barcode_input.grab_focus()

	if result.has("error"):
		_handle_error(result)
		ThemeManager.animate_error_shake(_barcode_input)
	else:
		var transactions = result.get("transactions", [])
		var title: String = ""
		if transactions.size() > 0:
			title = transactions[0].get("display_title", transactions[0].get("title", ""))

		# Refresh loans count first
		var loans_result = await API.get_current_loans(GS.current_borrower.get("borrower_id", ""))
		if not loans_result.has("error"):
			GS.current_loans = loans_result.get("loans", [])
			GS.current_borrower.current_loans_count = GS.current_loans.size()

		var warning_limit := int(GS.current_borrower.get("loan_limit_warning", 0))
		var current_count := int(GS.current_borrower.get("current_loans_count", 0))
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

func _handle_error(result: Dictionary) -> void:
	if result.has("detail") and result.detail is Dictionary:
		var code: String = result.detail.get("code", "")
		var details: Dictionary = result.detail.get("details", {})
		match code:
			"loan_limit_exceeded":
				_error_lbl.text = I18n.t("checkout.error_limit", {
					"current": int(details.get("current", 0)),
					"limit": int(details.get("limit", 3))
				})
			"loan_limit_warning_exceeded":
				_error_lbl.text = I18n.t("checkout.error_warning_limit", {
					"current": int(details.get("current", 0)),
					"limit": int(details.get("limit", 3))
				})
			"item_already_on_loan": _error_lbl.text = I18n.t("checkout.error_already_loaned")
			"borrower_blocked": _error_lbl.text = I18n.t("checkout.error_blocked")
			"borrower_has_overdue": _error_lbl.text = I18n.t("checkout.error_overdue")
			"item_not_found": _error_lbl.text = I18n.t("checkout.error_not_found")
			"item_not_available": _error_lbl.text = I18n.t("checkout.error_not_available")
			"item_not_loanable": _error_lbl.text = I18n.t("checkout.error_not_loanable")
			"item_reserved_for_other": _error_lbl.text = I18n.t("checkout.error_reserved")
			_: _error_lbl.text = I18n.t("common.error_unknown")
	else:
		_error_lbl.text = I18n.t("common.error_unknown")

func _update_breadcrumb() -> void:
	_breadcrumb.set_path([
		{"text": GS.library_name, "screen": "class_select", "clickable": true},
		{"text": GS.current_class.get("name", ""), "screen": "class_select", "clickable": true},
		{"text": "%s %s" % [GS.current_borrower.get("first_name", ""), GS.current_borrower.get("last_name", "")], "screen": "main_menu", "clickable": true},
		{"text": I18n.t("checkout.title"), "screen": "", "clickable": false}
	])

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

func _refresh_list() -> void:
	for c in _loans_list.get_children():
		c.queue_free()
	if GS.current_loans.is_empty():
		var lbl := Label.new()
		lbl.text = "Aucun emprunt"
		_loans_list.add_child(lbl)
		return
	for loan in GS.current_loans:
		var l := loan as Dictionary
		var lbl := Label.new()
		var display_title: String = l.get("display_title", l.get("title", ""))
		lbl.text = "\u2705 %s - %s" % [display_title, l.get("due_date", "")]
		_loans_list.add_child(lbl)

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		Mgr.pop()
		get_viewport().set_input_as_handled()
