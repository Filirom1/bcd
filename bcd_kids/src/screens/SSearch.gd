# Screen 6: Search with Autocomplete and Filters
extends Control

const BOOK_CARD = preload("res://src/components/BookCard.tscn")

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _breadcrumb: Breadcrumb = %Breadcrumb
@onready var _title_lbl: Label = %TitleLabel
@onready var _autocomplete: AutocompleteInput = %Autocomplete
@onready var _search_btn: Button = %SearchBtn
@onready var _filter_panel: FilterPanel = %FilterPanel
@onready var _count_lbl: Label = %CountLabel
@onready var _results_grid: GridContainer = %ResultsGrid

var _last_items: Array = []

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_title_lbl.text = I18n.t("search.title")

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(screen):
		if screen == "class_select": GS.reset_borrower()
		Mgr.replace(screen)
	)

	visibility_changed.connect(func():
		if visible:
			_update_breadcrumb()
			_autocomplete.focus_input()
			if not _last_items.is_empty():
				_display_results(_last_items)
	)

	_update_breadcrumb()

	_autocomplete.set_placeholder(I18n.t("search.placeholder"))
	_autocomplete.search_submitted.connect(func(q): _perform_search(q))
	_autocomplete.focus_input()

	_search_btn.pressed.connect(func(): _perform_search(_autocomplete.get_text()))

	_filter_panel.setup(GS.filter_medium_types, GS.filter_genres)
	_filter_panel.filters_changed.connect(_on_filters_changed)

func _update_breadcrumb() -> void:
	_breadcrumb.set_path([
		{"text": GS.library_name, "screen": "class_select", "clickable": true},
		{"text": GS.current_class.get("name", ""), "screen": "class_select", "clickable": true},
		{"text": "%s %s" % [GS.current_borrower.get("first_name", ""), GS.current_borrower.get("last_name", "")], "screen": "main_menu", "clickable": true},
		{"text": I18n.t("search.title"), "screen": "", "clickable": false}
	])

func _on_filters_changed(_filters: Dictionary) -> void:
	pass

func _perform_search(query: String) -> void:
	var filters := _filter_panel.get_filters()
	var result = await API.search_catalog(query, filters)
	if result.has("error"):
		_count_lbl.text = I18n.t("common.error_network")
		_clear_results()
		return
	_last_items = result.get("items", [])
	_count_lbl.text = I18n.t("search.results_count", {"count": _last_items.size()})
	_display_results(_last_items)

func _display_results(items: Array) -> void:
	_clear_results()
	if items.is_empty():
		var lbl := Label.new()
		lbl.text = "Aucun résultat"
		lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_results_grid.add_child(lbl)
		return
	for item in items:
		var card := BOOK_CARD.instantiate() as BookCard
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		_results_grid.add_child(card)
		var biblio_id := int(item.get("id", 0))
		# Find hold_id if already reserved
		var hold_id := _find_hold_id_for_biblio(biblio_id)
		if hold_id > 0:
			card.setup(item, I18n.t("hold.cancel"), ThemeManager.ERROR)
			card.theme_type_variation = "PanelWarning"
			card.action_clicked.connect(func(data): _on_cancel_clicked(data, hold_id))
		else:
			card.setup(item, I18n.t("search.reserve"), ThemeManager.SECONDARY)
			card.action_clicked.connect(_on_reserve_clicked)
		card.detail_clicked.connect(_on_detail_clicked)

func _find_hold_id_for_biblio(biblio_id: int) -> int:
	for hold in GS.current_holds:
		if int(hold.get("bibliographic_record_id", 0)) == biblio_id:
			return int(hold.get("id", 0))
	return 0

func _clear_results() -> void:
	for c in _results_grid.get_children():
		c.queue_free()

func _on_reserve_clicked(book_data: Dictionary) -> void:
	var borrower_db_id := int(GS.current_borrower.get("id", 0))
	var biblio_record_id := int(book_data.get("id", 0))
	var result = await API.create_hold(borrower_db_id, biblio_record_id)
	if result.has("error"):
		var error_msg := I18n.t("common.error_unknown")
		if result.has("detail") and result.detail is Dictionary:
			var code: String = result.detail.get("code", "")
			match code:
				"borrower_blocked":    error_msg = I18n.t("hold.error_blocked")
				"hold_already_exists": error_msg = I18n.t("hold.error_duplicate")
				"no_items_for_record": error_msg = I18n.t("hold.error_no_items")
				"hold_limit_exceeded": error_msg = I18n.t("hold.error_limit")
		Mgr.notify(error_msg, "error")
		return
	var holds = await API.get_holds(borrower_db_id)
	GS.current_holds = holds
	var title: String = book_data.get("title", "")
	if title.is_empty():
		Mgr.notify(I18n.t("hold.confirmed"), "success")
	else:
		Mgr.notify(I18n.t("hold.confirmed_with_title", {"title": title}), "success")
	Mgr.pop()

func _on_cancel_clicked(book_data: Dictionary, hold_id: int) -> void:
	await API.cancel_hold(hold_id)
	var borrower_db_id := int(GS.current_borrower.get("id", 0))
	var holds = await API.get_holds(borrower_db_id)
	GS.current_holds = holds
	var title: String = book_data.get("title", "")
	if title.is_empty():
		Mgr.notify(I18n.t("hold.cancelled"), "warning")
	else:
		Mgr.notify(I18n.t("hold.cancelled_with_title", {"title": title}), "warning")
	_display_results(_last_items)

func _on_detail_clicked(book_data: Dictionary) -> void:
	GS.current_class["_temp_book_data"] = book_data
	Mgr.push("book_detail")
