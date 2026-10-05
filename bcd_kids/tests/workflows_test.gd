extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const HTTP_SERVER = preload("res://tests/api_test_server.gd")

var _test := SUPPORT.new()
var _server: Node
var _api: Node
var _gs: Node
var _settings: Node
var _i18n: Node
var _mounted: Array = []
var _previous_base_url := ""
var _previous_library_name := ""
var _previous_nav_params: Dictionary = {}
var _previous_filter_medium_types: Array = []
var _previous_settings: Dictionary = {}
var _previous_borrower: Dictionary = {}
var _previous_class: Dictionary = {}
var _previous_loans: Array = []
var _previous_holds: Array = []


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	_api = get_root().get_node("API")
	_gs = get_root().get_node("GS")
	_settings = get_root().get_node("Settings")
	_i18n = get_root().get_node("I18n")
	_save_state()

	_server = HTTP_SERVER.new()
	get_root().add_child(_server)
	if not _server.call("start"):
		_test.expect(false, "Workflow HTTP fixture starts")
		_restore_state()
		_test.finish(self)
		return
	await _test.wait_frames(self)
	_gs.base_url = "http://127.0.0.1:%d/api/v1" % int(_server.get("port"))
	_gs.library_name = "School Library"
	_gs.current_class = {"id": 1, "name": "CE1"}
	_gs.current_borrower = {
		"id": 42,
		"borrower_id": "ST-42",
		"first_name": "Alice",
		"last_name": "Reader",
		"current_loans_count": 0,
		"loan_limit": 3,
		"loan_limit_warning": 2,
	}
	_gs.current_loans = []
	_gs.current_holds = []
	_gs.settings = {"item_barcode_prefix": ".", "borrower_barcode_prefix": "%"}

	await _test_checkout_successes()
	await _test_return_successes()
	await _test_search_and_holds()
	await _test_name_and_class_workflows()
	await _test_main_menu_actions()

	for node_variant in _mounted:
		if node_variant is Node and is_instance_valid(node_variant):
			(node_variant as Node).queue_free()
	await _test.wait_frames(self, 3)
	_server.call("stop")
	_server.queue_free()
	_restore_state()
	_test.finish(self)


func _save_state() -> void:
	_previous_base_url = str(_gs.get("base_url"))
	_previous_library_name = str(_gs.get("library_name"))
	_previous_nav_params = (_gs.get("nav_params") as Dictionary).duplicate(true)
	_previous_filter_medium_types = (_gs.get("filter_medium_types") as Array).duplicate(true)
	_previous_settings = (_gs.get("settings") as Dictionary).duplicate(true)
	_previous_borrower = (_gs.get("current_borrower") as Dictionary).duplicate(true)
	_previous_class = (_gs.get("current_class") as Dictionary).duplicate(true)
	_previous_loans = (_gs.get("current_loans") as Array).duplicate(true)
	_previous_holds = (_gs.get("current_holds") as Array).duplicate(true)


func _restore_state() -> void:
	_gs.set("base_url", _previous_base_url)
	_gs.set("library_name", _previous_library_name)
	_gs.set("nav_params", _previous_nav_params)
	_gs.set("filter_medium_types", _previous_filter_medium_types)
	_gs.set("settings", _previous_settings)
	_gs.set("current_borrower", _previous_borrower)
	_gs.set("current_class", _previous_class)
	_gs.set("current_loans", _previous_loans)
	_gs.set("current_holds", _previous_holds)


func _clear_fixture() -> void:
	_server.call("clear_routes")
	_server.get("requests").clear()


func _enqueue_json(path: String, status_code: int, data, headers := {}) -> void:
	_server.call("enqueue", path, status_code, JSON.stringify(data), headers)

func _enqueue_raw(path: String, status_code: int, body: String, headers := {}) -> void:
	_server.call("enqueue", path, status_code, body, headers)

func _clear_notifications() -> void:
	var manager: Node = get_root().get_node("Mgr")
	var box: VBoxContainer = manager.get("_notif_box")
	if box == null:
		return
	for child in box.get_children():
		box.remove_child(child)
		child.queue_free()


func _mount(path: String) -> Control:
	var screen: Control = load(path).instantiate()
	get_root().add_child(screen)
	_mounted.append(screen)
	await _test.wait_frames(self, 8)
	await _wait_until_http_idle()
	return screen


func _wait_until_http_idle() -> void:
	var idle_frames := 0
	for _index in range(180):
		await _test.wait_frames(self)
		if int(_api.get("in_flight_requests")) == 0:
			idle_frames += 1
			if idle_frames >= 3:
				return
		else:
			idle_frames = 0


func _last_notification_text() -> String:
	var manager: Node = get_root().get_node("Mgr")
	var box: VBoxContainer = manager.get("_notif_box")
	if box == null or box.get_child_count() == 0:
		return ""
	var notification: Node = box.get_child(box.get_child_count() - 1)
	var label := notification.get_node_or_null("MessageLabel") as Label
	return label.text if label != null else ""


func _last_request_containing(fragment: String) -> Dictionary:
	var requests: Array = _server.get("requests")
	for index in range(requests.size() - 1, -1, -1):
		var request: Dictionary = requests[index]
		if str(request.get("target", "")).contains(fragment):
			return request
	return {}


func _test_checkout_successes() -> void:
	var checkout: Control = await _mount("res://src/screens/SCheckout.tscn")
	var input: LineEdit = checkout.get_node("MainMargin/Root/InputRow/BarcodeInput")
	var loans: VBoxContainer = checkout.get_node("MainMargin/Root/LoanScroll/LoansList")

	_clear_fixture()
	_enqueue_json("/api/v1/circulation/checkout", 200, {
		"transactions": [{"display_title": "The Dragon"}],
	})
	_enqueue_json("/api/v1/circulation/borrower/ST-42/items", 200, {
		"loans": [{"display_title": "The Dragon", "due_date": "2026-07-01"}],
	})
	input.text = ". DR-1"
	await checkout.call("_do_checkout")
	await _test.wait_frames(self, 2)
	var checkout_request := _last_request_containing("/circulation/checkout")
	_test.equal(
		JSON.parse_string(checkout_request.get("body", "")).get("item_ids", []),
		["DR-1"],
		"Checkout removes the configured barcode prefix and spaces"
	)
	_test.equal(_gs.current_loans.size(), 1, "Checkout success refreshes the current loan list")
	_test.equal(loans.get_child_count(), 1, "Checkout success renders the refreshed loan list")
	_test.expect(_last_notification_text().contains("The Dragon"), "Checkout success includes the returned title")

	_clear_fixture()
	_gs.current_borrower.current_loans_count = 1
	_gs.current_borrower.loan_limit_warning = 1
	_enqueue_json("/api/v1/circulation/checkout", 200, {"transactions": [{}]})
	_enqueue_json("/api/v1/circulation/borrower/ST-42/items", 200, {
		"loans": [
			{"display_title": "The Dragon", "due_date": "2026-07-01"},
			{"display_title": "Mystery Book", "due_date": "2026-07-02"},
		],
	})
	input.text = ".MYSTERY-2"
	await checkout.call("_do_checkout")
	await _test.wait_frames(self, 2)
	_test.equal(_gs.current_borrower.current_loans_count, 2, "Checkout updates the borrower loan counter")
	_test.expect(
		_last_notification_text() == _i18n.call("t", "checkout.success_warning"),
		"Checkout uses the warning message when the threshold is reached without a title"
	)
	_test.equal(loans.get_child_count(), 2, "Checkout refreshes all visible loan rows")


func _test_return_successes() -> void:
	var return_scan: Control = await _mount("res://src/screens/SReturnScan.tscn")
	var input: LineEdit = return_scan.get_node("MainMargin/Root/InputRow/BarcodeInput")
	var history: VBoxContainer = return_scan.get_node("MainMargin/Root/HistoryScroll/HistoryContainer")

	_clear_fixture()
	_enqueue_json("/api/v1/circulation/return", 200, {
		"items": [{
			"display_title": "Returned Book",
			"borrower_name": "Bob Reader",
			"was_overdue": true,
			"days_overdue": 4,
			"shelf_location": "Romans",
			"call_number": "843",
		}],
	})
	_enqueue_json("/api/v1/circulation/borrower/ST-42/items", 200, {"loans": []})
	input.text = ".RETURN-1"
	await return_scan.call("_do_return")
	await _test.wait_frames(self, 3)
	_test.equal(_gs.current_loans, [], "Return success refreshes the borrower's loans")
	_test.expect(_last_notification_text() == _i18n.call("t", "return.success_with_title", {"title": "Returned Book"}), "Return success includes the title")
	_test.expect(history.get_child_count() >= 1, "Return success adds an item to return history")
	if history.get_child_count() > 0:
		var entry: VBoxContainer = history.get_child(history.get_child_count() - 1)
		_test.expect(entry.get_child_count() >= 2, "Return history renders location badges when shelf data exists")

	_clear_fixture()
	_enqueue_json("/api/v1/circulation/return", 200, {
		"items": [{
			"title": "Ready Book",
			"borrower_name": "Bob Reader",
			"hold_ready": {
				"borrower_name": "Claire Student",
				"class_name": "CM1",
				"borrower_id": "ST-99",
			},
		}],
	})
	_enqueue_json("/api/v1/circulation/borrower/ST-42/items", 200, {
		"loans": [{"display_title": "Remaining", "due_date": "2026-08-01"}],
	})
	input.text = ".RETURN-2"
	await return_scan.call("_do_return")
	await _test.wait_frames(self, 3)
	var hold_ready: Dictionary = _gs.nav_params.get("hold_ready", {})
	_test.equal(hold_ready.get("borrower_name", ""), "Claire Student", "Return stores a ready hold for the teacher")
	_test.equal(_gs.current_borrower.current_loans_count, 1, "Return updates the borrower count after a second return")
	var ready_screen := get_root().get_node_or_null("Mgr/SHoldReady")
	_test.expect(ready_screen != null, "Return navigates to the ready-hold screen")
	if ready_screen != null:
		_test.equal(
			ready_screen.get_node("MainMargin/Center/Content/InfoPanel/InfoContent/BookTitleLabel").text,
			"Ready Book",
			"Ready-hold screen displays the returned title"
		)


func _find_hold(biblio_id: int) -> bool:
	for hold in _gs.current_holds:
		if hold is Dictionary and int(hold.get("bibliographic_record_id", 0)) == biblio_id:
			return true
	return false


func _test_search_and_holds() -> void:
	_gs.current_holds = [{"id": 7, "bibliographic_record_id": 3}]
	var search: Control = await _mount("res://src/screens/SSearch.tscn")
	_clear_fixture()
	_enqueue_json("/api/v1/catalog/bibliographic/search", 200, {
		"items": [
			{"id": 1, "title": "Available", "authors": ["Author"], "available_copies": 2},
			{"id": 2, "title": "Unavailable", "authors": [], "publisher": "Publisher", "available_copies": 0},
			{"id": 3, "title": "Already held", "authors": ["Author"], "available_copies": 0},
		],
	})
	await search.call("_perform_search", "dragons")
	await _test.wait_frames(self, 2)
	var results: GridContainer = search.get_node("MainMargin/Root/ResultsScroll/ResultsGrid")
	_test.equal(results.get_child_count(), 3, "Search renders available, unavailable, and already-held results")
	if results.get_child_count() == 3:
		var available: Control = results.get_child(0)
		var unavailable: Control = results.get_child(1)
		var held: Control = results.get_child(2)
		_test.equal(
			available.get_node("Content/Info/StatusRow/StatusLabel").text,
			"🟢 " + str(_i18n.call("t", "search.status_available")),
			"Search labels an available book"
		)
		_test.equal(
			unavailable.get_node("Content/Info/StatusRow/StatusLabel").text,
			"🔴 " + str(_i18n.call("t", "search.status_on_loan")),
			"Search labels an unavailable book"
		)
		_test.expect(available.get_node("Content/Info/BtnRow/ActionBtn").visible, "Search shows Reserve for an available book")
		_test.equal(available.get_node("Content/Info/BtnRow/ActionBtn").text, _i18n.call("t", "search.reserve"), "Search labels available books with Reserve")
		_test.equal(held.get_node("Content/Info/BtnRow/ActionBtn").text, _i18n.call("t", "hold.cancel"), "Search changes the action for an already-held book")
		_test.expect(held.theme_type_variation == "PanelWarning", "Search highlights an already-held result")

	var book := {"id": 1, "title": "Available", "authors": ["Author"], "available_copies": 2}
	_clear_fixture()
	_enqueue_json("/api/v1/holds", 201, {"id": 11, "queue_position": 1})
	_enqueue_json("/api/v1/holds/borrower/42", 200, [{"id": 11, "bibliographic_record_id": 1, "title": "Available"}])
	await search.call("_on_reserve_clicked", book)
	_test.equal(_gs.current_holds.size(), 1, "Successful reservation refreshes the borrower's holds")
	_test.expect(_last_notification_text().contains("Available"), "Successful reservation includes the book title")

	_clear_fixture()
	_enqueue_json("/api/v1/holds", 201, {"id": 12, "queue_position": 2})
	_enqueue_json("/api/v1/holds/borrower/42", 500, {"error": "refresh failed"})
	await search.call("_on_reserve_clicked", {"id": 2, "title": "Unavailable"})
	_test.expect(_find_hold(2), "Reservation remains local after a successful POST and failed refresh")
	_test.equal(_last_notification_text(), _i18n.call("t", "common.refresh_failed"), "Reservation reports a refresh failure separately")

	var hold_error_keys := {
		"network_error": "common.error_network",
		"borrower_blocked": "hold.error_blocked",
		"hold_already_exists": "hold.error_duplicate",
		"no_items_for_record": "hold.error_no_items",
		"hold_limit_exceeded": "hold.error_limit",
		"unmapped": "common.error_unknown",
	}
	for code in hold_error_keys:
		_clear_fixture()
		_clear_notifications()
		_enqueue_json("/api/v1/holds", 409, {
			"success": false,
			"error_code": str(code).to_upper(),
			"context": {},
		})
		await search.call("_on_reserve_clicked", book)
		_test.equal(
			_last_notification_text(),
			_i18n.call("t", hold_error_keys[code]),
			"Reservation maps the server error for " + code
		)

	_gs.current_holds = [{"id": 7, "bibliographic_record_id": 3}]
	_clear_fixture()
	_enqueue_raw("/api/v1/holds/7", 204, "")
	_enqueue_json("/api/v1/holds/borrower/42", 200, [])
	await search.call("_on_cancel_clicked", {"id": 3, "title": "Already held"}, 7)
	_test.equal(_gs.current_holds, [], "Cancelling a hold refreshes the hold list")
	_test.expect(_last_notification_text().contains("Already held"), "Cancellation includes the book title")

	_gs.current_holds = [{"id": 8, "bibliographic_record_id": 2, "title": "Unavailable"}]
	_clear_fixture()
	_enqueue_raw("/api/v1/holds/8", 204, "")
	_enqueue_json("/api/v1/holds/borrower/42", 500, {"error": "refresh failed"})
	await search.call("_on_cancel_clicked", {"id": 2, "title": "Unavailable"}, 8)
	_test.expect(not _find_hold(2), "Cancellation remains local after a successful DELETE and failed refresh")
	_test.equal(_last_notification_text(), _i18n.call("t", "common.refresh_failed"), "Cancellation reports a refresh failure separately")

	_clear_fixture()
	_enqueue_json("/api/v1/catalog/bibliographic/3", 200, {"id": 3, "title": "Already held", "authors": ["Author"]})
	await search.call("_on_detail_clicked", {"id": 3, "title": "Already held", "authors": ["Author"]})
	await _test.wait_frames(self, 10)
	_test.equal(
		_gs.nav_params.get("book_data", {}).get("title", ""),
		"Already held",
		"Search stores navigation book data before opening details"
	)


func _test_name_and_class_workflows() -> void:
	_clear_fixture()
	_enqueue_json("/api/v1/classes", 200, [
		{"id": 1, "name": "CM2", "average_age": 9},
		{"id": 2, "name": "CE1 B", "average_age": 7},
		{"id": 3, "name": "CP", "average_age": 6},
		{"id": 4, "name": "CE1 A", "average_age": 7},
		{"id": 5, "name": "No age"},
	])
	var class_select: Control = await _mount("res://src/screens/SClassSelect.tscn")
	var classes: GridContainer = class_select.get_node("MainMargin/Root/ClassesGrid")
	await _test.wait_frames(self, 2)
	var class_names: Array = []
	for button in classes.get_children():
		if button is Button:
			class_names.append(button.get_node("Content/ClassNameLabel").text)
	_test.equal(class_names, ["CP", "CE1 A", "CE1 B", "CM2", "No age"], "Class selection sorts by age and then name")

	_clear_fixture()
	_enqueue_json("/api/v1/circulation/return", 200, {"items": [{"title": "Quick return"}]})
	class_select.call("_handle_scan", ".ITEM-9")
	await _wait_until_http_idle()
	var quick_request := _last_request_containing("/circulation/return")
	var quick_body = JSON.parse_string(quick_request.get("body", ""))
	_test.equal(
		quick_body.get("item_ids", []) if quick_body is Dictionary else [],
		["ITEM-9"],
		"Item barcode scanning performs a quick return without a borrower"
	)

	_clear_fixture()
	_enqueue_json("/api/v1/circulation/return", 200, {"items": [{"title": "Typed return"}]})
	class_select.call("_handle_scan", "RAW-ITEM")
	await _wait_until_http_idle()
	var typed_return_request := _last_request_containing("/circulation/return")
	var typed_return_body = JSON.parse_string(typed_return_request.get("body", ""))
	_test.equal(
		typed_return_body.get("item_ids", []) if typed_return_body is Dictionary else [],
		["RAW-ITEM"],
		"Typing an item ID without its configured prefix performs a quick return"
	)

	_server.get("requests").clear()
	class_select.call("_handle_scan", ".")
	await _test.wait_frames(self, 3)
	_test.equal(_server.get("requests").size(), 0, "A barcode containing only its prefix is ignored")
	_gs.settings["item_barcode_prefix"] = ""
	_clear_fixture()
	_enqueue_json("/api/v1/circulation/return", 200, {"items": []})
	class_select.call("_handle_scan", "RAW-ITEM")
	await _wait_until_http_idle()
	var empty_prefix_request := _last_request_containing("/circulation/return")
	var empty_prefix_body = JSON.parse_string(empty_prefix_request.get("body", ""))
	_test.equal(
		empty_prefix_body.get("item_ids", []) if empty_prefix_body is Dictionary else [],
		["RAW-ITEM"],
		"An empty item prefix continues to accept raw item IDs"
	)
	_gs.settings["item_barcode_prefix"] = "."

	var name_input: Control = await _mount("res://src/screens/SNameInput.tscn")
	var name_edit: LineEdit = name_input.get_node("MainMargin/Root/FormCenter/Form/SearchInput")
	var name_error: Label = name_input.get_node("MainMargin/Root/FormCenter/Form/ErrorLabel")
	var candidates: VBoxContainer = name_input.get_node("MainMargin/Root/FormCenter/Form/CandidatesContainer")

	_clear_fixture()
	_enqueue_json("/api/v1/borrowers", 200, {"items": []})
	name_edit.text = "Al"
	await name_input.call("_search")
	_test.equal(name_error.text, _i18n.call("t", "name_input.not_found"), "Student search reports zero matches")

	_clear_fixture()
	_enqueue_json("/api/v1/borrowers", 200, [])
	name_edit.text = "Al"
	await name_input.call("_search")
	_test.equal(name_error.text, _i18n.call("t", "common.error_unknown"), "Student search rejects a response with the wrong JSON shape")

	_clear_fixture()
	_enqueue_json("/api/v1/borrowers", 200, {"items": [
		{"id": 9, "first_name": "Alex", "last_name": "One", "current_loans_count": 0},
		{"id": 10, "first_name": "Alex", "last_name": "Two", "current_loans_count": 2},
	]})
	name_edit.text = "Al"
	await name_input.call("_search")
	await _test.wait_frames(self, 3)
	_test.equal(candidates.get_child_count(), 3, "Student search renders multiple matches for disambiguation")
	_test.expect((candidates.get_child(2) as Button).text.contains("2"), "Student choice displays the loan count")

	_clear_fixture()
	_enqueue_json("/api/v1/borrowers", 500, "server failure")
	name_edit.text = "Al"
	await name_input.call("_search")
	_test.equal(name_error.text, _i18n.call("t", "common.error_network"), "Student search reports a network error")

	_clear_fixture()
	_enqueue_json("/api/v1/borrowers", 200, {"items": [{"id": 8, "borrower_id": "ST-8", "first_name": "Alex", "last_name": "One"}]})
	_enqueue_json("/api/v1/circulation/borrower/ST-8/items", 404, "")
	_enqueue_json("/api/v1/holds/borrower/8", 404, "")
	name_edit.text = "Al"
	await name_input.call("_search")
	await _wait_until_http_idle()
	_test.equal(_gs.current_borrower.get("borrower_id", ""), "ST-8", "Student search logs in directly for one match")

	_clear_fixture()
	_enqueue_json("/api/v1/borrowers/CARD-7", 200, {
		"id": 7,
		"borrower_id": "ST-7",
		"first_name": "Sam",
		"last_name": "Scanner",
		"class_id": 4,
		"class_name": "CE1 A",
	})
	_enqueue_json("/api/v1/circulation/borrower/ST-7/items", 404, "")
	_enqueue_json("/api/v1/holds/borrower/7", 404, "")
	class_select.call("_handle_scan", "%CARD-7")
	await _wait_until_http_idle()
	_test.equal(_gs.current_borrower.get("borrower_id", ""), "ST-7", "Borrower barcode login selects the returned borrower")
	_test.equal(_gs.current_class.get("name", ""), "CE1 A", "Borrower barcode login selects the returned class")
	await _test.wait_frames(self, 30)


func _test_main_menu_actions() -> void:
	_gs.current_borrower = {
		"id": 42,
		"borrower_id": "ST-42",
		"first_name": "Alice",
		"last_name": "Reader",
		"current_loans_count": 2,
		"loan_limit": 3,
		"loan_limit_warning": 2,
	}
	_clear_fixture()
	_enqueue_json("/api/v1/circulation/borrower/ST-42/items", 200, {"loans": [{"item_id": "A-1", "display_title": "Book"}]})
	_enqueue_json("/api/v1/holds/borrower/42", 200, [])
	var main_menu: Control = await _mount("res://src/screens/SMainMenu.tscn")

	_clear_fixture()
	_enqueue_json("/api/v1/circulation/renew", 200, {"renewed": [{"new_due_date": "2026-09-01"}]})
	_enqueue_json("/api/v1/circulation/borrower/ST-42/items", 200, {"loans": [{"item_id": "A-1", "due_date": "2026-09-01"}]})
	await main_menu.call("_renew_item", "A-1")
	_test.expect(_last_notification_text().contains("2026-09-01"), "Main-menu renewal success displays the new due date")

	var renewal_error_keys := {
		"NO_RENEWABLE_ITEMS": "main_menu.renew_no_items",
		"UNKNOWN_RENEWAL_ERROR": "common.error_unknown",
	}
	for code in renewal_error_keys:
		_clear_fixture()
		_clear_notifications()
		_enqueue_json("/api/v1/circulation/renew", 409, {"error_code": code, "context": {}})
		await main_menu.call("_renew_item", "A-1")
		_test.equal(
			_last_notification_text(),
			_i18n.call("t", renewal_error_keys[code]),
			"Main-menu renewal maps the server error for " + code
		)

	var theme_manager: Node = get_root().get_node("ThemeManager")
	_gs.current_borrower.current_loans_count = 2
	_gs.current_borrower.loan_limit_warning = 2
	main_menu.call("_update_counter")
	_test.equal(main_menu.get_node("MainMargin/Scroll/Root/HeaderInfo/CountLabel").get_theme_color("font_color"), theme_manager.get("WARNING"), "Main-menu counter uses warning colour at the threshold")
	_gs.current_borrower.current_loans_count = 3
	main_menu.call("_update_counter")
	_test.equal(main_menu.get_node("MainMargin/Scroll/Root/HeaderInfo/CountLabel").get_theme_color("font_color"), theme_manager.get("ERROR"), "Main-menu counter uses error colour at the loan limit")
