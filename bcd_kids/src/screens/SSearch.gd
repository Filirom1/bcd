# Screen 6: Search with Autocomplete and Filters
extends Control

const BOOK_CARD = preload("res://src/components/BookCard.tscn")
const EMPTY_STATE = preload("res://src/components/EmptyState.tscn")
const CIRCULATION = preload("res://src/utils/CirculationHelper.gd")
const DATA = preload("res://src/utils/DataHelper.gd")
const ERROR_MESSAGES = preload("res://src/utils/ErrorMessages.gd")
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")

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
var _search_request_id := 0
var _action_busy := false
var _owner_key := ""

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_title_lbl.text = I18n.t("search.title")
	_back_btn.text = "← " + I18n.t("common.back")

	_back_btn.pressed.connect(func(): Mgr.pop())

	_breadcrumb.crumb_clicked.connect(func(screen):
		if screen == "class_select": GS.reset_borrower()
		Mgr.replace(screen)
	)

	_update_breadcrumb()

	_autocomplete.set_placeholder(I18n.t("search.placeholder"))
	_autocomplete.search_submitted.connect(func(q): _perform_search(q))
	_autocomplete.focus_input()

	_search_btn.pressed.connect(func(): _perform_search(_autocomplete.get_text()))

	_filter_panel.setup(GS.filter_medium_types)
	_filter_panel.filters_changed.connect(_on_filters_changed)
	_owner_key = _current_owner_key()

# Refresh labels when this existing stack entry becomes visible again. Search
# results are intentionally preserved when returning from book details.
func on_enter() -> void:
	var owner_key := _current_owner_key()
	if not _owner_key.is_empty() and owner_key != _owner_key:
		_last_items.clear()
		_clear_results()
		_count_lbl.text = ""
	_owner_key = owner_key
	_title_lbl.text = I18n.t("search.title")
	_back_btn.text = "← " + I18n.t("common.back")
	_autocomplete.set_placeholder(I18n.t("search.placeholder"))
	_update_breadcrumb()
	if not _last_items.is_empty():
		_display_results(_last_items)
	_autocomplete.focus_input()

func _current_owner_key() -> String:
	return "%s:%s" % [str(GS.base_url), str(GS.current_borrower.get("borrower_id", ""))]

func _update_breadcrumb() -> void:
	_breadcrumb.set_path(CIRCULATION.borrower_breadcrumb(I18n.t("search.title")))

func _on_filters_changed(_filters: Dictionary) -> void:
	# Filters are actionable controls, so changing one immediately refreshes the
	# current query instead of silently waiting for a second search click.
	_perform_search(_autocomplete.get_text())

func _perform_search(query: String) -> void:
	_search_request_id += 1
	var request_id := _search_request_id
	var generation := Mgr.navigation_generation
	var result = await API.search_catalog(query, _filter_panel.get_filters())
	if not is_inside_tree() or request_id != _search_request_id \
			or not Mgr.is_generation_current(generation):
		return
	if not (result is Dictionary) or result.has("error"):
		_count_lbl.text = ERROR_MESSAGES.message(result, ERROR_MESSAGES.COMMON)
		_clear_results()
		return
	var items = result.get("items", [])
	if not (items is Array):
		_count_lbl.text = I18n.t("common.error_unknown")
		_clear_results()
		return
	_last_items = items
	_count_lbl.text = I18n.t("search.results_count", {"count": _last_items.size()})
	_display_results(_last_items)

func _display_results(items: Array) -> void:
	_clear_results()
	if items.is_empty():
		var empty_message := EMPTY_STATE.instantiate() as EmptyState
		_results_grid.add_child(empty_message)
		empty_message.setup(I18n.t("search.no_results"))
		return
	for item in items:
		if not (item is Dictionary):
			continue
		var card := BOOK_CARD.instantiate() as BookCard
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		_results_grid.add_child(card)
		var biblio_id := int(item.get("id", 0))
		# Find hold_id if already reserved.
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
		if hold is Dictionary and int(hold.get("bibliographic_record_id", 0)) == biblio_id:
			return int(hold.get("id", 0))
	return 0

func _clear_results() -> void:
	NODE_HELPER.clear_children(_results_grid)

func _on_reserve_clicked(book_data: Dictionary) -> void:
	if _action_busy:
		return
	_action_busy = true
	var generation := Mgr.navigation_generation
	var borrower_db_id := int(GS.current_borrower.get("id", 0))
	var biblio_record_id := int(book_data.get("id", 0))
	var result = await API.create_hold(borrower_db_id, biblio_record_id)
	if not is_inside_tree() or not Mgr.is_generation_current(generation):
		_action_busy = false
		return
	if result is Dictionary and result.has("error"):
		Mgr.notify(ERROR_MESSAGES.message(result, ERROR_MESSAGES.HOLD), "error")
		_action_busy = false
		return

	var title := DATA.display_title(book_data)
	if title.is_empty():
		Mgr.notify(I18n.t("hold.confirmed"), "success")
	else:
		Mgr.notify(I18n.t("hold.confirmed_with_title", {"title": title}), "success")

	# The POST succeeded. Keep an optimistic local hold so a failed refresh does
	# not make the student retry an operation that has already been created.
	var local_hold_id := int(result.get("id", 0))
	if local_hold_id == 0:
		local_hold_id = -biblio_record_id if biblio_record_id > 0 else -1
	var optimistic_hold := {
		"id": local_hold_id,
		"bibliographic_record_id": biblio_record_id,
		"title": title,
		"authors": book_data.get("authors", []),
		"queue_position": int(result.get("queue_position", 0)),
		"status": "pending",
	}
	var optimistic_holds := GS.current_holds.duplicate(true)
	optimistic_holds.append(optimistic_hold)
	GS.current_holds = optimistic_holds

	var holds = await API.get_holds(borrower_db_id)
	if not is_inside_tree() or not Mgr.is_generation_current(generation):
		_action_busy = false
		return
	if holds is Array:
		GS.current_holds = holds
	else:
		Mgr.notify(I18n.t("common.refresh_failed"), "warning")
	_action_busy = false
	Mgr.pop()

func _on_cancel_clicked(book_data: Dictionary, hold_id: int) -> void:
	if _action_busy:
		return
	_action_busy = true
	var generation := Mgr.navigation_generation
	var result = await API.cancel_hold(hold_id)
	if not is_inside_tree() or not Mgr.is_generation_current(generation):
		_action_busy = false
		return
	if result is Dictionary and result.has("error"):
		Mgr.notify(ERROR_MESSAGES.message(result, ERROR_MESSAGES.HOLD), "error")
		_action_busy = false
		return

	# The DELETE succeeded; remove the hold locally before trying to refresh.
	var remaining: Array = []
	for hold in GS.current_holds:
		if not (hold is Dictionary) or int(hold.get("id", 0)) != hold_id:
			remaining.append(hold)
	GS.current_holds = remaining
	var title := DATA.display_title(book_data)
	if title.is_empty():
		Mgr.notify(I18n.t("hold.cancelled"), "warning")
	else:
		Mgr.notify(I18n.t("hold.cancelled_with_title", {"title": title}), "warning")

	var borrower_db_id := int(GS.current_borrower.get("id", 0))
	var holds = await API.get_holds(borrower_db_id)
	if not is_inside_tree() or not Mgr.is_generation_current(generation):
		_action_busy = false
		return
	if holds is Array:
		GS.current_holds = holds
	else:
		Mgr.notify(I18n.t("common.refresh_failed"), "warning")
	_action_busy = false
	_display_results(_last_items)

func _on_detail_clicked(book_data: Dictionary) -> void:
	GS.set_nav_param("book_data", book_data)
	Mgr.push("book_detail")

func _input(event: InputEvent) -> void:
	if not (event is InputEventKey and event.pressed and not event.echo):
		return
	if not _autocomplete.is_input_focused():
		return
	if event.keycode in [KEY_DOWN, KEY_UP, KEY_LEFT, KEY_RIGHT]:
		var cards := _results_grid.get_children()
		if not cards.is_empty() and cards[0] is BookCard:
			(cards[0] as BookCard).grab_first_focus()
			accept_event()

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		var viewport := get_viewport()
		if viewport != null:
			viewport.set_input_as_handled()
		Mgr.pop()
