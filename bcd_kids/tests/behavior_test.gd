extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const THEME_MANAGER_SCRIPT = preload("res://autoload/ThemeManager.gd")

var _test := SUPPORT.new()
var _gs: Node
var _settings: Node
var _theme_manager: Node
var _previous_gs_state: Dictionary = {}
var _previous_settings_state: Dictionary = {}
var _previous_theme := ""


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	_save_global_state()
	await _test_navigation_manager()
	await _test_keyboard_and_empty_inputs()
	await _test_cover_fallbacks()
	await _test_search_actions()
	await _test_borrower_actions()
	await _test_theme_animations()
	_restore_global_state()
	_test.finish(self)


func _save_global_state() -> void:
	_gs = get_root().get_node("GS")
	_settings = get_root().get_node("Settings")
	_theme_manager = get_root().get_node("ThemeManager")
	_previous_gs_state = {
		"base_url": _gs.get("base_url"),
		"library_name": _gs.get("library_name"),
		"current_class": (_gs.get("current_class") as Dictionary).duplicate(true),
		"current_borrower": (_gs.get("current_borrower") as Dictionary).duplicate(true),
		"current_loans": (_gs.get("current_loans") as Array).duplicate(true),
		"current_holds": (_gs.get("current_holds") as Array).duplicate(true),
		"settings": (_gs.get("settings") as Dictionary).duplicate(true),
		"filter_medium_types": (_gs.get("filter_medium_types") as Array).duplicate(true),
		"nav_params": (_gs.get("nav_params") as Dictionary).duplicate(true),
	}
	_previous_settings_state = {
		"theme": _settings.get("theme"),
		"graphics_quality": _settings.get("graphics_quality"),
		"resolution": _settings.get("resolution"),
	}
	_previous_theme = str(_theme_manager.get("current_theme_name"))


func _restore_global_state() -> void:
	for key in _previous_gs_state:
		_gs.set(key, _previous_gs_state[key])
	for key in _previous_settings_state:
		_settings.set(key, _previous_settings_state[key])
	_theme_manager.call("set_theme", _previous_theme)
	_settings.call("save_settings")


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
	_test.equal(_stack_names(manager), ["class_select"], "Manager replaces without leaving an orphaned screen")

	manager.call("push", "main_menu")
	manager.call("replace", "class_select")
	_test.equal(_stack_names(manager), ["class_select"], "Manager reuses an existing target instead of duplicating it")

	manager.call("push", "main_menu")
	manager.call("push", "checkout")
	manager.call("pop_to", "main_menu")
	_test.equal(_stack_names(manager), ["class_select", "main_menu"], "Manager pops to an existing breadcrumb target")
	manager.call("reset_to", "class_select")
	_test.equal(_stack_names(manager), ["class_select"], "Manager reset_to clears the entire navigation stack")
	await _test.wait_frames(self, 2)

func _stack_names(manager: Node) -> Array:
	var names: Array = []
	for screen in manager.get("_stack"):
		names.append(screen.get_meta("screen_name", ""))
	return names


func _test_keyboard_and_empty_inputs() -> void:
	var class_select: Control = await _mount("res://src/screens/SClassSelect.tscn")
	class_select.call("_handle_scan", "   ")
	class_select.call("_quick_return", "")
	class_select.call("_login_by_card", "")
	class_select.call("_input", _escape_event())
	_test.equal(class_select.get_node("MainMargin/Root/ScanRow/ScanInput").text, "", "Class selection clears empty scans")
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
	var detail: Control = await _mount("res://src/screens/SBookDetail.tscn")
	detail.call("_load_cover", "missing.jpg")
	detail.call("_on_cover_failed")
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
	_test.equal(
		_gs.get("nav_params").get("book_data", {}).get("title", ""),
		"Unavailable",
		"Search stores book data before opening details"
	)
	search.call("_input", _escape_event())
	search.call("_unhandled_key_input", _escape_event())
	var i18n: Node = get_root().get_node("I18n")
	_test.equal(search.get_node("MainMargin/Root/CountLabel").text, i18n.call("t", "common.error_network"), "Search reports a network error")
	await _unmount(search)


func _test_borrower_actions() -> void:
	var gs: Node = get_root().get_node("GS")
	var main_menu: Control = await _mount("res://src/screens/SMainMenu.tscn")
	main_menu.call("_show_book_detail", {"bibliographic_record_id": 4, "title": "Book"})
	_test.equal(gs.get("nav_params").get("book_data", {}).get("title", ""), "Book", "Main menu stores navigation book data before opening details")
	await main_menu.call("_renew_item", "missing")
	main_menu.call("_unhandled_key_input", _escape_event())
	await _unmount(main_menu)

	var holds: Control = await _mount("res://src/screens/SMyHolds.tscn")
	gs.set("current_holds", [{"id": 1, "title": "Hold"}])
	await holds.call("_cancel_hold", 1)
	holds.call("_input", _escape_event())
	holds.call("_unhandled_key_input", _escape_event())
	_test.equal(gs.get("current_holds").size(), 1, "My holds preserves its data when cancellation fails")
	await _unmount(holds)

	var ready: Control = await _mount("res://src/screens/SHoldReady.tscn")
	ready.call("_go_back")
	ready.call("_unhandled_key_input", _escape_event())
	await _unmount(ready)

	var settings: Control = await _mount("res://src/screens/SSettings.tscn")
	settings.call("_on_carousel_apply")
	_test.equal(_settings.get("theme"), _theme_manager.get("current_theme_name"), "Settings apply stores the active theme")
	settings.call("_on_back")
	settings.call("_unhandled_key_input", _escape_event())
	_test.expect(is_instance_valid(settings), "Settings remains valid while handling back input")
	await _unmount(settings)


func _test_theme_animations() -> void:
	var pop_node := Control.new()
	get_root().add_child(pop_node)
	THEME_MANAGER_SCRIPT.animate_pop_in(pop_node)
	_test.equal(pop_node.scale, Vector2(0.5, 0.5), "Pop-in animation starts from a reduced scale")
	_test.equal(pop_node.modulate.a, 0.0, "Pop-in animation starts transparent")
	await _test.wait_frames(self, 30)
	_test.expect(pop_node.scale.x > 0.5, "Pop-in animation advances its scale")

	var flash_node := Control.new()
	get_root().add_child(flash_node)
	THEME_MANAGER_SCRIPT.animate_success_flash(flash_node)
	await _test.wait_frames(self, 90)
	_test.equal(flash_node.modulate, Color.WHITE, "Success flash restores the original modulation")

	var shake_node := Control.new()
	get_root().add_child(shake_node)
	THEME_MANAGER_SCRIPT.animate_error_shake(shake_node)
	await _test.wait_frames(self, 60)
	_test.equal(shake_node.scale, Vector2.ONE, "Error shake restores the original scale")

	pop_node.queue_free()
	flash_node.queue_free()
	shake_node.queue_free()


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
