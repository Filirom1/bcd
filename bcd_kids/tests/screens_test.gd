extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const I18N_SCRIPT = preload("res://autoload/I18n.gd")

var _test := SUPPORT.new()
var _screens: Array = []


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	_test_scene_contracts()
	await _mount_screens()
	await _test_checkout_screen()
	await _test_return_screen()
	await _test_name_input_screen()
	await _test_search_screen()
	await _test_book_detail_screen()
	await _test_main_menu_screen()
	await _test_holds_screen()
	await _test_settings_screen()
	await _free_screens()
	_test.finish(self)


func _test_scene_contracts() -> void:
	var scene_paths := [
		"res://src/screens/SClassSelect.tscn",
		"res://src/screens/SNameInput.tscn",
		"res://src/screens/SNameChoice.tscn",
		"res://src/screens/SMainMenu.tscn",
		"res://src/screens/SCheckout.tscn",
		"res://src/screens/SReturnScan.tscn",
		"res://src/screens/SSearch.tscn",
		"res://src/screens/SHoldConfirm.tscn",
		"res://src/screens/SHoldReady.tscn",
		"res://src/screens/SReturnShelve.tscn",
		"res://src/screens/SBookCover.tscn",
		"res://src/screens/SBookDetail.tscn",
		"res://src/screens/SMyHolds.tscn",
		"res://src/screens/SSettings.tscn",
	]
	for path in scene_paths:
		var packed = load(path)
		_test.expect(packed != null, "Screen scene loads: " + path)
		if packed == null:
			continue
		var screen: Node = packed.instantiate()
		_test.expect(screen.get_class() == "Control", "Screen root is Control: " + path)
		screen.free()


func _mount_screens() -> void:
	var gs: Node = get_root().get_node("GS")
	gs.set("library_name", "School Library")
	gs.set("current_class", {"id": 1, "name": "CE1"})
	gs.set("current_borrower", {
		"id": 42,
		"borrower_id": "ST-42",
		"first_name": "Alice",
		"last_name": "Reader",
		"current_loans_count": 0,
		"loan_limit": 3,
		"loan_limit_warning": 2,
	})
	gs.set("current_loans", [])
	gs.set("current_holds", [])
	gs.set("base_url", "")

	var paths := [
		"res://src/screens/SClassSelect.tscn",
		"res://src/screens/SNameInput.tscn",
		"res://src/screens/SNameChoice.tscn",
		"res://src/screens/SMainMenu.tscn",
		"res://src/screens/SCheckout.tscn",
		"res://src/screens/SReturnScan.tscn",
		"res://src/screens/SSearch.tscn",
		"res://src/screens/SHoldConfirm.tscn",
		"res://src/screens/SHoldReady.tscn",
		"res://src/screens/SReturnShelve.tscn",
		"res://src/screens/SBookCover.tscn",
		"res://src/screens/SBookDetail.tscn",
		"res://src/screens/SMyHolds.tscn",
		"res://src/screens/SSettings.tscn",
	]
	for path in paths:
		var screen = load(path).instantiate()
		_screens.append(screen)
		get_root().add_child(screen)
		await _test.wait_frames(self, 2)
		_test.expect(screen.is_inside_tree(), "Screen enters the tree: " + path)

	var i18n = I18N_SCRIPT.new()
	i18n.load_translations()
	_test.equal(
		(get_root().get_node("SClassSelect/MainMargin/Root/TitleLabel") as Label).text,
		i18n.t("class_select.title"),
		"Class selection initializes its translated title"
	)
	_test.equal(
		(get_root().get_node("SNameInput/MainMargin/Root/FormCenter/Form/SearchInput") as LineEdit).placeholder_text,
		i18n.t("name_input.placeholder"),
		"Name input initializes its translated placeholder"
	)


func _test_checkout_screen() -> void:
	var screen: Control = get_root().get_node("SCheckout")
	var gs: Node = get_root().get_node("GS")
	var theme_manager: Node = get_root().get_node("ThemeManager")
	var error_label: Label = screen.get_node("MainMargin/Root/ErrorLabel")
	for code in [
		"loan_limit_exceeded",
		"loan_limit_warning_exceeded",
		"item_already_on_loan",
		"borrower_blocked",
		"borrower_has_overdue",
		"item_not_found",
		"item_not_available",
		"item_not_loanable",
		"item_reserved_for_other",
		"unknown",
	]:
		screen.call("_handle_error", {"error": true, "detail": {"code": code, "details": {"current": 2, "limit": 3}}})
		_test.expect(not error_label.text.is_empty(), "Checkout displays an error for " + code)
	screen.call("_handle_error", {"error": true})
	_test.expect(not error_label.text.is_empty(), "Checkout handles an error without details")

	gs.set("current_borrower", {"current_loans_count": 2, "loan_limit": 3, "loan_limit_warning": 2})
	screen.call("_update_counter")
	_test.equal(screen.get_node("MainMargin/Root/CountLabel").get_theme_color("font_color"), theme_manager.get("WARNING"), "Checkout uses warning colour at the soft limit")
	gs.set("current_borrower", {"current_loans_count": 3, "loan_limit": 3, "loan_limit_warning": 2})
	screen.call("_update_counter")
	_test.equal(screen.get_node("MainMargin/Root/CountLabel").get_theme_color("font_color"), theme_manager.get("ERROR"), "Checkout uses error colour at the hard limit")
	gs.set("current_loans", [])
	screen.call("_refresh_list")
	await _test.wait_frames(self)
	_test.equal(screen.get_node("MainMargin/Root/LoanScroll/LoansList").get_child_count(), 1, "Checkout displays an empty-loans message")
	gs.set("current_loans", [{"title": "Book", "due_date": "2026-06-01"}])
	screen.call("_refresh_list")
	await _test.wait_frames(self)
	_test.equal(screen.get_node("MainMargin/Root/LoanScroll/LoansList").get_child_count(), 1, "Checkout renders a loan row")
	await _test.wait_frames(self)


func _test_return_screen() -> void:
	var screen: Control = get_root().get_node("SReturnScan")
	var error_label: Label = screen.get_node("MainMargin/Root/ErrorLabel")
	for code in ["item_not_found", "item_not_on_loan", "unknown"]:
		screen.call("_handle_error", {"error": true, "detail": {"code": code}})
		_test.expect(not error_label.text.is_empty(), "Return displays an error for " + code)
	screen.call("_handle_error", {"error": true})
	_test.expect(not error_label.text.is_empty(), "Return handles an error without details")

	var history: VBoxContainer = screen.get_node("MainMargin/Root/HistoryScroll/HistoryContainer")
	var initial_count := history.get_child_count()
	screen.call("_add_to_history", "Returned Book", "Alice Reader", false, 0, "Romans", "843")
	await _test.wait_frames(self)
	_test.expect(history.get_child_count() >= 1 and history.get_child(0) is VBoxContainer, "Return adds an on-time item to history")
	screen.call("_add_to_history", "Late Book", "Bob Reader", true, 4, "", "")
	await _test.wait_frames(self)
	_test.expect(history.get_child_count() >= 2, "Return adds an overdue item to history")


func _test_name_input_screen() -> void:
	var screen: Control = get_root().get_node("SNameInput")
	var search_input: LineEdit = screen.get_node("MainMargin/Root/FormCenter/Form/SearchInput")
	var candidates: VBoxContainer = screen.get_node("MainMargin/Root/FormCenter/Form/CandidatesContainer")
	search_input.text = "Al"
	screen.call("_show_candidates", [
		{"first_name": "Alice", "last_name": "Reader", "current_loans_count": 0},
		{"first_name": "Alice", "last_name": "Writer", "current_loans_count": 1},
		{"first_name": "Alex", "last_name": "Author", "current_loans_count": 3},
	])
	_test.equal(candidates.get_child_count(), 4, "Name input renders the duplicate-name hint and candidates")
	_test.expect(not (candidates.get_child(1) as Button).text.is_empty(), "Name input renders the zero-loans candidate")
	_test.expect((candidates.get_child(2) as Button).text.contains("1"), "Name input renders the one-loan candidate")
	_test.expect((candidates.get_child(3) as Button).text.contains("3"), "Name input renders the plural-loans candidate")
	screen.call("_clear_candidates")
	await _test.wait_frames(self)
	_test.equal(candidates.get_child_count(), 0, "Name input clears candidates")


func _test_search_screen() -> void:
	var screen: Control = get_root().get_node("SSearch")
	var gs: Node = get_root().get_node("GS")
	gs.set("current_holds", [{"id": 7, "bibliographic_record_id": 12}])
	_test.equal(int(screen.call("_find_hold_id_for_biblio", 12)), 7, "Search finds a hold by bibliographic record")
	_test.equal(int(screen.call("_find_hold_id_for_biblio", 99)), 0, "Search returns no hold for an unrelated record")
	var results: GridContainer = screen.get_node("MainMargin/Root/ResultsScroll/ResultsGrid")
	screen.call("_display_results", [])
	await _test.wait_frames(self)
	_test.equal(results.get_child_count(), 1, "Search displays an empty-results message")
	screen.call("_display_results", [{"id": 12, "title": "Reserved", "authors": ["Author"], "available_copies": 0}])
	await _test.wait_frames(self)
	_test.expect(results.get_child_count() >= 1, "Search renders a result card")
	screen.call("_clear_results")
	await _test.wait_frames(self)
	_test.equal(results.get_child_count(), 0, "Search clears result cards")


func _test_book_detail_screen() -> void:
	var screen: Control = get_root().get_node("SBookDetail")
	var fields: VBoxContainer = screen.get_node("MainMargin/Root/Body/FieldsScroll/FieldsContainer")
	screen.call("_build_fields", {
		"title": "Book",
		"subtitle": "A subtitle",
		"authors": ["Author 1", "Author 2"],
		"illustrators": ["Illustrator"],
		"publisher": "Publisher",
		"publication_year": 2026,
		"collection": "Collection",
		"series_number": 2,
		"level": "CE1",
		"medium_type": "Livre",
		"page_count": 48,
		"keywords": ["dragons", "adventure"],
		"description": "A description.",
		"shelf_location": "Romans",
		"call_number": "843",
	})
	await _test.wait_frames(self)
	_test.expect(fields.get_child_count() >= 14, "Book detail renders populated bibliographic fields")
	screen.call("_show_no_cover")
	_test.expect(screen.get_node("MainMargin/Root/Body/CoverCol/CoverImage").visible == false, "Book detail hides a missing cover")
	_test.expect(screen.get_node("MainMargin/Root/Body/CoverCol/NoCoverLabel").visible, "Book detail shows its missing-cover label")


func _test_main_menu_screen() -> void:
	var screen: Control = get_root().get_node("SMainMenu")
	var gs: Node = get_root().get_node("GS")
	var loans: VBoxContainer = screen.get_node("MainMargin/Scroll/Root/LoansContainer")
	gs.set("current_loans", [])
	screen.call("_refresh_loans")
	await _test.wait_frames(self)
	_test.equal(loans.get_child_count(), 1, "Main menu displays the empty-loans message")
	gs.set("current_loans", [{"item_id": "A-1", "display_title": "Book", "authors": ["Author"], "due_date": "2026-06-01", "is_overdue": false}])
	screen.call("_refresh_loans")
	await _test.wait_frames(self, 2)
	_test.equal(loans.get_child_count(), 1, "Main menu renders a loan card")
	gs.set("current_borrower", {"first_name": "Alice", "last_name": "Reader", "current_loans_count": 0, "loan_limit": 3, "loan_limit_warning": 2})
	screen.call("_update_name")
	screen.call("_update_counter")
	_test.equal(screen.get_node("MainMargin/Scroll/Root/HeaderInfo/NameLabel").text, "Alice Reader", "Main menu displays the borrower name")
	_test.expect(screen.get_node("MainMargin/Scroll/Root/HeaderInfo/CountLabel").text.contains("0"), "Main menu displays the loan counter")


func _test_holds_screen() -> void:
	var screen: Control = get_root().get_node("SMyHolds")
	var gs: Node = get_root().get_node("GS")
	var holds: VBoxContainer = screen.get_node("MainMargin/Root/HoldsScroll/HoldsContainer")
	gs.set("current_holds", [])
	screen.call("_refresh_holds")
	await _test.wait_frames(self)
	_test.equal(holds.get_child_count(), 1, "My holds displays the empty-holds message")
	gs.set("current_holds", [{"id": 3, "title": "Reserved", "authors": ["Author"], "status": "pending", "queue_position": 2}])
	screen.call("_refresh_holds")
	await _test.wait_frames(self, 2)
	_test.equal(holds.get_child_count(), 1, "My holds renders a hold card")

	var ready = get_root().get_node("SHoldReady") as Control
	_test.equal(ready.get_node("MainMargin/Center/Content/InfoPanel/InfoContent/BookTitleLabel").text, "", "Hold-ready screen handles missing hold data")
	var shelve = get_root().get_node("SReturnShelve") as Control
	_test.equal(shelve.get_node("MainMargin/Center/Content/InfoPanel/InfoContent/ShelfRow/ShelfLabel").text, "-", "Return-shelve screen defaults a missing shelf")
	_test.equal(shelve.get_node("MainMargin/Center/Content/InfoPanel/InfoContent/CallRow/CallLabel").text, "-", "Return-shelve screen defaults a missing call number")


func _test_settings_screen() -> void:
	var screen: Control = get_root().get_node("SSettings")
	var name_label: Label = screen.get_node("MainMargin/Root/SettingsPanel/SettingsScroll/PanelContent/ThemeCarousel/CarouselRow/ThemeNameLabel")
	var index_label: Label = screen.get_node("MainMargin/Root/SettingsPanel/SettingsScroll/PanelContent/ThemeCarousel/ThemeIndexLabel")
	var initial_name := name_label.text
	screen.call("_on_carousel_next")
	_test.expect(name_label.text != initial_name, "Settings carousel advances to another theme")
	screen.call("_on_carousel_prev")
	_test.equal(name_label.text, initial_name, "Settings carousel returns to its previous theme")
	_test.expect(not index_label.text.is_empty(), "Settings carousel displays its index or random hint")


func _free_screens() -> void:
	for screen_variant in _screens:
		if screen_variant is Node and is_instance_valid(screen_variant):
			(screen_variant as Node).queue_free()
	await _test.wait_frames(self, 2)
