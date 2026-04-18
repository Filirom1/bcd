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

	_update_breadcrumb()
	_update_name()
	_load_holds()

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

	_load_holds()
