# Screen 1: Class Selection
extends Control

const CLASS_BTN = preload("res://src/components/ClassButton.tscn")

@onready var _bg: ColorRect = %Background
@onready var _server_btn: Button = %ServerBtn
@onready var _settings_btn: Button = %SettingsBtn
@onready var _fr_btn: Button = %FrBtn
@onready var _en_btn: Button = %EnBtn
@onready var _title_lbl: Label = %TitleLabel
@onready var _scan_input: LineEdit = %ScanInput
@onready var _classes_grid: GridContainer = %ClassesGrid

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_title_lbl.text = I18n.t("class_select.title")

	var lib_name: String = GS.library_name if not GS.library_name.is_empty() else I18n.t("common.home")
	_server_btn.text = lib_name
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
	visibility_changed.connect(func():
		if visible: _scan_input.call_deferred("grab_focus")
	)

	_load_classes()

func _handle_scan(text: String) -> void:
	var t := text.strip_edges()
	_scan_input.clear()
	_scan_input.call_deferred("grab_focus")
	if t.is_empty():
		return
	var item_pfx: String = GS.settings.get("item_barcode_prefix", ".")
	var borrower_pfx: String = GS.settings.get("borrower_barcode_prefix", "%")
	if t.begins_with(item_pfx):
		_quick_return(t.substr(item_pfx.length()))
	elif t.begins_with(borrower_pfx):
		_login_by_card(t.substr(borrower_pfx.length()))

func _quick_return(item_id: String) -> void:
	if item_id.is_empty():
		return
	var result = await API.return_items([item_id])
	if result.has("error"):
		Mgr.notify(I18n.t("return.error_not_on_loan"), "error")
		ThemeManager.animate_error_shake(_scan_input)
	else:
		var items = result.get("items", [])
		var title: String = ""
		if items.size() > 0:
			title = items[0].get("title", "")

		if title.is_empty():
			Mgr.notify(I18n.t("return.success"), "success")
		else:
			Mgr.notify(I18n.t("return.success_with_title", {"title": title}), "success")

		if items.size() > 0:
			var hold_ready = items[0].get("hold_ready", null)
			if hold_ready != null and hold_ready is Dictionary:
				GS.current_class["_temp_hold_ready"] = {
					"title": items[0].get("title", ""),
					"borrower_name": hold_ready.get("borrower_name", ""),
					"class_name": hold_ready.get("class_name", ""),
					"borrower_id": hold_ready.get("borrower_id", "")
				}
				Mgr.push("hold_ready")

		ThemeManager.animate_success_flash(_scan_input)
	_scan_input.call_deferred("grab_focus")

func _login_by_card(card_id: String) -> void:
	if card_id.is_empty():
		return
	var result = await API.get_borrower(card_id)
	if result.has("error"):
		Mgr.notify(I18n.t("name_input.not_found"), "error")
		ThemeManager.animate_error_shake(_scan_input)
		_scan_input.call_deferred("grab_focus")
		return
	GS.current_class = {
		"id": result.get("class_id", 0),
		"name": result.get("class_name", ""),
		"homeroom_teacher": result.get("homeroom_teacher", "")
	}
	GS.current_borrower = result
	Mgr.push("main_menu")

func _load_classes() -> void:
	var classes = await API.get_classes()

	if classes.is_empty():
		var lbl := Label.new()
		lbl.text = I18n.t("class_select.no_classes")
		lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_classes_grid.add_child(lbl)
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

func _refresh_ui() -> void:
	_title_lbl.text = I18n.t("class_select.title")
	_scan_input.placeholder_text = I18n.t("class_select.scan_placeholder")
	for c in _classes_grid.get_children():
		c.queue_free()
	_load_classes()
