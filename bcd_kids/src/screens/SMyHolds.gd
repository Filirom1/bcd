# Screen 7: My Holds (Reservations)
extends Control

const HOLD_CARD = preload("res://src/components/HoldCard.tscn")

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _breadcrumb: Breadcrumb = %Breadcrumb
@onready var _title_lbl: Label = %TitleLabel
@onready var _name_lbl: Label = %NameLabel
@onready var _holds_container: VBoxContainer = %HoldsContainer

func _ready() -> void:
	_bg.color = ThemeManager.BG

	_title_lbl.text = I18n.t("main_menu.my_holds")

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(screen):
		if screen == "class_select": GS.reset_borrower()
		Mgr.replace(screen)
	)

	visibility_changed.connect(func():
		if visible:
			_update_breadcrumb()
			_update_name()
	)

	_back_btn.focus_entered.connect(func():
		_back_btn.add_theme_stylebox_override("normal", _back_btn.get_theme_stylebox("hover"))
		_back_btn.add_theme_color_override("font_color", ThemeManager.TEXT)
	)
	_back_btn.focus_exited.connect(func():
		_back_btn.remove_theme_stylebox_override("normal")
		_back_btn.remove_theme_color_override("font_color")
	)

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

func _load_holds() -> void:
	var holds = await API.get_holds(GS.current_borrower.get("id", 0))
	GS.current_holds = holds
	_refresh_holds()

func _refresh_holds() -> void:
	for c in _holds_container.get_children():
		c.queue_free()

	if GS.current_holds.is_empty():
		var lbl := Label.new()
		lbl.text = I18n.t("main_menu.no_holds")
		_holds_container.add_child(lbl)
		return

	for hold in GS.current_holds:
		var card := HOLD_CARD.instantiate() as HoldCard
		_holds_container.add_child(card)
		card.setup(hold as Dictionary)
		card.cancel_clicked.connect(_cancel_hold)

func _update_breadcrumb() -> void:
	_breadcrumb.set_path([
		{"text": GS.library_name, "screen": "class_select", "clickable": true},
		{"text": GS.current_class.get("name", ""), "screen": "class_select", "clickable": true},
		{"text": "%s %s" % [GS.current_borrower.get("first_name", ""), GS.current_borrower.get("last_name", "")], "screen": "main_menu", "clickable": true},
		{"text": I18n.t("main_menu.my_holds"), "screen": "", "clickable": false}
	])

func _update_name() -> void:
	_name_lbl.text = "%s %s" % [GS.current_borrower.get("first_name", ""), GS.current_borrower.get("last_name", "")]

func _cancel_hold(hold_id: int) -> void:
	var hold_title: String = ""
	for hold in GS.current_holds:
		if hold.get("id", 0) == hold_id:
			hold_title = hold.get("title", "")
			break

	await API.cancel_hold(hold_id)

	if hold_title.is_empty():
		Mgr.notify(I18n.t("hold.cancelled"), "warning")
	else:
		Mgr.notify(I18n.t("hold.cancelled_with_title", {"title": hold_title}), "warning")

	await _load_holds()
	_back_btn.call_deferred("grab_focus")
