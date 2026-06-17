# Screen 5: Return by Scan
extends Control

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

func _ready() -> void:
	_bg.color = ThemeManager.BG

	_title_lbl.text = I18n.t("return.title")
	_input_lbl.text = I18n.t("return.label")
	_history_title.text = I18n.t("return.returned_today")

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(screen):
		if screen == "class_select": GS.reset_borrower()
		Mgr.replace(screen)
	)

	_barcode_input.keep_editing_on_text_submit = true
	_barcode_input.text_submitted.connect(func(_t): _do_return())
	_validate_btn.pressed.connect(func(): _do_return())
	_barcode_input.call_deferred("grab_focus")
	visibility_changed.connect(func():
		if visible:
			_update_breadcrumb()
			_barcode_input.call_deferred("grab_focus")
	)

	_update_breadcrumb()

	var placeholder_lbl := Label.new()
	placeholder_lbl.text = I18n.t("return.scan_books_placeholder")
	_history.add_child(placeholder_lbl)

func _do_return() -> void:
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
		_error_lbl.text = I18n.t("return.error_not_found")
		ThemeManager.animate_error_shake(_barcode_input)
		return

	var result = await API.return_items([item_id])

	_barcode_input.grab_focus()

	if result.has("error"):
		_handle_error(result)
		ThemeManager.animate_error_shake(_barcode_input)
	else:
		var items = result.get("items", [])
		if items.size() > 0:
			var item := items[0] as Dictionary
			var was_overdue: bool = item.get("was_overdue", false)
			var days_overdue: int = item.get("days_overdue", 0)
			var borrower_name: String = item.get("borrower_name", "")
			var title: String = item.get("display_title", item.get("title", ""))
			var _sl = item.get("shelf_location")
			var _cn = item.get("call_number")
			var shelf: String = (str(_sl) if _sl != null else "").strip_edges()
			var call_num: String = (str(_cn) if _cn != null else "").strip_edges()
			_add_to_history(title, borrower_name, was_overdue, days_overdue, shelf, call_num)

			if title.is_empty():
				Mgr.notify(I18n.t("return.success"), "success")
			else:
				Mgr.notify(I18n.t("return.success_with_title", {"title": title}), "success")

			var hold_ready = item.get("hold_ready", null)
			if hold_ready != null and hold_ready is Dictionary:
				GS.current_class["_temp_hold_ready"] = {
					"title": item.get("display_title", item.get("title", "")),
					"borrower_name": hold_ready.get("borrower_name", ""),
					"class_name": hold_ready.get("class_name", ""),
					"borrower_id": hold_ready.get("borrower_id", "")
				}
				Mgr.push("hold_ready")

			ThemeManager.animate_success_flash(_barcode_input)
			var loans_result = await API.get_current_loans(GS.current_borrower.get("borrower_id", ""))
			if not loans_result.has("error"):
				GS.current_loans = loans_result.get("loans", [])
				GS.current_borrower.current_loans_count = GS.current_loans.size()
			_barcode_input.grab_focus()

func _handle_error(result: Dictionary) -> void:
	if result.has("detail") and result.detail is Dictionary:
		match result.detail.get("code", ""):
			"item_not_found": _error_lbl.text = I18n.t("return.error_not_found")
			"item_not_on_loan": _error_lbl.text = I18n.t("return.error_not_on_loan")
			_: _error_lbl.text = I18n.t("common.error_unknown")
	else:
		_error_lbl.text = I18n.t("common.error_unknown")

func _update_breadcrumb() -> void:
	_breadcrumb.set_path([
		{"text": GS.library_name, "screen": "class_select", "clickable": true},
		{"text": GS.current_class.get("name", ""), "screen": "class_select", "clickable": true},
		{"text": "%s %s" % [GS.current_borrower.get("first_name", ""), GS.current_borrower.get("last_name", "")], "screen": "main_menu", "clickable": true},
		{"text": I18n.t("return.title"), "screen": "", "clickable": false}
	])

func _add_to_history(
	title: String,
	borrower_name: String,
	was_late: bool,
	days_overdue: int,
	shelf: String,
	call_num: String
) -> void:
	if _history.get_child_count() == 1 and _history.get_child(0) is Label:
		_history.get_child(0).queue_free()

	var entry := VBoxContainer.new()
	entry.add_theme_constant_override("separation", 2)
	_history.add_child(entry)

	# Status line
	var status_text := I18n.t("return.late", {"days": days_overdue}) if was_late else I18n.t("return.on_time")
	var icon := "⚠️" if was_late else "✅"
	var lbl := Label.new()
	lbl.text = "%s %s · %s · %s" % [icon, title, borrower_name, status_text]
	entry.add_child(lbl)

	# Location badges
	if not shelf.is_empty() or not call_num.is_empty():
		var loc_row := HBoxContainer.new()
		loc_row.add_theme_constant_override("separation", 6)
		entry.add_child(loc_row)

		var loc_lbl := Label.new()
		loc_lbl.text = I18n.t("return.ranger_a")
		loc_lbl.theme_type_variation = "LabelSmall"
		loc_row.add_child(loc_lbl)

		var badges := HBoxContainer.new()
		badges.add_theme_constant_override("separation", 4)
		loc_row.add_child(badges)
		BadgeHelper.populate_badges(badges, shelf, call_num)

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		Mgr.pop()
		get_viewport().set_input_as_handled()
