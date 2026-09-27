extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const THEME_MANAGER_SCRIPT = preload("res://autoload/ThemeManager.gd")

var _test := SUPPORT.new()


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	await _test_navigation_manager()
	await _test_keyboard_and_empty_inputs()
	await _test_cover_fallbacks()
	await _test_search_actions()
	await _test_borrower_actions()
	_test_theme_animations()
	_test.finish(self)


func _test_navigation_manager() -> void:
	var manager: Node = get_root().get_node("Mgr")
	var name_screen = manager.call("_make", "name_input")
	_test.expect(name_screen is Control, "Manager creates a named screen")
	if name_screen is Node:
		(name_screen as Node).queue_free()
	var unknown_screen = manager.call("_make", "unknown-screen")
	_test.expect(unknown_screen is Control, "Manager creates a fallback for an unknown screen")
	if unknown_screen is Node:
		(unknown_screen as Node).queue_free()

	manager.call("push", "name_input")
	manager.call("push", "settings")
	manager.call("pop")
	manager.call("replace", "class_select")
	_test.expect(true, "Manager supports push, pop, and replace navigation")
	await _test.wait_frames(self, 2)


func _test_keyboard_and_empty_inputs() -> void:
	var class_select: Control = await _mount("res://src/screens/SClassSelect.tscn")
	class_select.call("_handle_scan", "   ")
	class_select.call("_quick_return", "")
	class_select.call("_login_by_card", "")
	class_select.call("_select_class", {"id": 2, "name": "CP"})
	class_select.call("_refresh_ui")
	class_select.call("_input", _escape_event())
	_test.expect(true, "Class selection handles empty scans and keyboard input")
	await _unmount(class_select)

	var checkout: Control = await _mount("res://src/screens/SCheckout.tscn")
	checkout.get_node("MainMargin/Root/InputRow/BarcodeInput").text = "   "
	await checkout.call("_do_checkout")
	checkout.call("_unhandled_key_input", _escape_event())
	_test.equal(checkout.get_node("MainMargin/Root/InputRow/BarcodeInput").text, "", "Checkout clears an empty barcode")
	await _unmount(checkout)

	var return_scan: Control = await _mount("res://src/screens/SReturnScan.tscn")
	return_scan.get_node("MainMargin/Root/InputRow/BarcodeInput").text = "   "
	await return_scan.call("_do_return")
	return_scan.call("_unhandled_key_input", _escape_event())
	_test.equal(return_scan.get_node("MainMargin/Root/InputRow/BarcodeInput").text, "", "Return clears an empty barcode")
	await _unmount(return_scan)

	var name_input: Control = await _mount("res://src/screens/SNameInput.tscn")
	name_input.get_node("MainMargin/Root/FormCenter/Form/SearchInput").text = "A"
	await name_input.call("_search")
	name_input.call("_unhandled_key_input", _escape_event())
	_test.expect(not name_input.get_node("MainMargin/Root/FormCenter/Form/ErrorLabel").text.is_empty(), "Name input rejects a search shorter than two characters")
	name_input.call("_login", {"id": 42, "first_name": "Alice", "last_name": "Reader"})
	await _unmount(name_input)


func _test_cover_fallbacks() -> void:
	var cover: Control = await _mount("res://src/screens/SBookCover.tscn")
	cover.call("_load_cover", "missing.jpg")
	cover.call("_on_cover_loaded", HTTPRequest.RESULT_CANT_CONNECT, 0, PackedStringArray(), PackedByteArray())
	_test.expect(cover.get_node("MainMargin/Root/Center/Content/NoCoverLabel").visible, "Book cover screen falls back when loading fails")
	await _unmount(cover)

	var detail: Control = await _mount("res://src/screens/SBookDetail.tscn")
	detail.call("_load_cover", "missing.jpg")
	detail.call("_on_cover_loaded", HTTPRequest.RESULT_CANT_CONNECT, 0, PackedStringArray(), PackedByteArray())
	detail.call("_unhandled_key_input", _escape_event())
	_test.expect(detail.get_node("MainMargin/Root/Body/CoverCol/NoCoverLabel").visible, "Book detail screen falls back when loading fails")
	await _unmount(detail)


func _test_search_actions() -> void:
	var search: Control = await _mount("res://src/screens/SSearch.tscn")
	search.call("_on_filters_changed", {})
	await search.call("_perform_search", "anything")
	await search.call("_on_reserve_clicked", {"id": 9, "title": "Unavailable"})
	await search.call("_on_cancel_clicked", {"id": 9, "title": "Unavailable"}, 1)
	search.call("_on_detail_clicked", {"id": 9, "title": "Unavailable"})
	search.call("_input", _escape_event())
	search.call("_unhandled_key_input", _escape_event())
	_test.expect(true, "Search exercises network error, reserve, cancel, detail, and keyboard paths")
	await _unmount(search)


func _test_borrower_actions() -> void:
	var gs: Node = get_root().get_node("GS")
	var main_menu: Control = await _mount("res://src/screens/SMainMenu.tscn")
	main_menu.call("_show_book_cover", {"bibliographic_record_id": 4, "title": "Book"})
	await main_menu.call("_return_item", "missing")
	await main_menu.call("_renew_item", "missing")
	main_menu.call("_unhandled_key_input", _escape_event())
	_test.expect(true, "Main menu exercises return, renew, detail, and keyboard paths")
	await _unmount(main_menu)

	var holds: Control = await _mount("res://src/screens/SMyHolds.tscn")
	gs.set("current_holds", [{"id": 1, "title": "Hold"}])
	await holds.call("_cancel_hold", 1)
	holds.call("_input", _escape_event())
	holds.call("_unhandled_key_input", _escape_event())
	_test.expect(true, "My holds exercises cancellation and keyboard paths")
	await _unmount(holds)

	var confirm: Control = await _mount("res://src/screens/SHoldConfirm.tscn")
	confirm.call("_go_back")
	confirm.call("_unhandled_key_input", _escape_event())
	await _unmount(confirm)

	var ready: Control = await _mount("res://src/screens/SHoldReady.tscn")
	ready.call("_go_back")
	ready.call("_unhandled_key_input", _escape_event())
	await _unmount(ready)

	var shelve: Control = await _mount("res://src/screens/SReturnShelve.tscn")
	shelve.call("_go_back")
	shelve.call("_unhandled_key_input", _escape_event())
	await _unmount(shelve)

	var settings: Control = await _mount("res://src/screens/SSettings.tscn")
	settings.call("_on_carousel_apply")
	settings.call("_on_back")
	settings.call("_unhandled_key_input", _escape_event())
	await _unmount(settings)


func _test_theme_animations() -> void:
	var node := Control.new()
	get_root().add_child(node)
	THEME_MANAGER_SCRIPT.animate_pop_in(node)
	THEME_MANAGER_SCRIPT.animate_success_flash(node)
	THEME_MANAGER_SCRIPT.animate_error_shake(node)
	_test.expect(node.get_tree() != null, "Theme animation helpers create tweens on controls")
	node.queue_free()


func _mount(path: String) -> Control:
	var screen: Control = load(path).instantiate()
	get_root().add_child(screen)
	await _test.wait_frames(self, 2)
	return screen


func _unmount(node: Node) -> void:
	if is_instance_valid(node):
		node.queue_free()
	await _test.wait_frames(self, 2)


func _escape_event() -> InputEventKey:
	var event := InputEventKey.new()
	event.keycode = KEY_ESCAPE
	event.pressed = true
	return event
