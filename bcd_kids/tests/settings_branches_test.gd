extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const SETTINGS_SCRIPT = preload("res://autoload/Settings.gd")

var _test := SUPPORT.new()
var _settings: Node
var _theme_manager: Node
var _original_theme := ""
var _original_quality := ""
var _original_resolution := ""
var _original_last_url := ""
var _original_last_name := ""
var _original_user_file := ""


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	_settings = get_root().get_node("Settings")
	_theme_manager = get_root().get_node("ThemeManager")
	_test_autoload_order_and_theme_restore()
	_original_theme = str(_settings.get("theme"))
	_original_quality = str(_settings.get("graphics_quality"))
	_original_resolution = str(_settings.get("resolution"))
	_original_last_url = str(_settings.get("last_server_url"))
	_original_last_name = str(_settings.get("last_library_name"))
	var original_file := FileAccess.open(SETTINGS_SCRIPT.SETTINGS_FILE, FileAccess.READ)
	if original_file != null:
		_original_user_file = original_file.get_as_text()
		original_file.close()

	_test_corrupt_and_partial_files()
	await _test_settings_buttons_and_preview()
	_restore_settings()
	_test.finish(self)


func _test_autoload_order_and_theme_restore() -> void:
	var project_file := FileAccess.open("res://project.godot", FileAccess.READ)
	if project_file == null:
		_test.expect(false, "Project configuration is readable for autoload-order regression")
		return
	var project_text := project_file.get_as_text()
	project_file.close()
	_test.expect(
		project_text.find('ThemeManager="*res://autoload/ThemeManager.gd"')
			< project_text.find('Settings="*res://autoload/Settings.gd"'),
		"ThemeManager autoloads before Settings"
	)
	_test.equal(
		str(_theme_manager.get("current_theme_name")),
		str(_settings.get("theme")),
		"Settings reapplies the saved theme after autoload initialization"
	)


func _test_corrupt_and_partial_files() -> void:
	var corrupt := FileAccess.open(SETTINGS_SCRIPT.SETTINGS_FILE, FileAccess.WRITE)
	corrupt.store_string("this is not a ConfigFile")
	corrupt.close()
	var recovered = SETTINGS_SCRIPT.new()
	recovered.load_settings()
	_test.equal(recovered.get("graphics_quality"), "low", "Corrupt settings fall back to the default quality")
	_test.equal(recovered.get("resolution"), "maximized", "Corrupt settings fall back to the default resolution")
	_test.equal(recovered.get("theme"), "forest", "Corrupt settings fall back to the default theme")

	var partial_config := ConfigFile.new()
	partial_config.set_value("graphics", "quality", "high")
	partial_config.set_value("display", "theme", "forest")
	partial_config.save(SETTINGS_SCRIPT.SETTINGS_FILE)
	var partial = SETTINGS_SCRIPT.new()
	partial.load_settings()
	_test.equal(partial.get("graphics_quality"), "high", "Settings load a present key from a partial file")
	_test.equal(partial.get("resolution"), "maximized", "Settings default a missing resolution key")
	_test.equal(partial.get("last_server_url"), "", "Settings default missing server keys")
	_test.equal(partial.get("auth_scheme"), "basic", "Settings default a missing auth scheme")


func _test_settings_buttons_and_preview() -> void:
	_settings.set("theme", "forest")
	_settings.set("graphics_quality", "low")
	_settings.set("resolution", "maximized")
	_theme_manager.call("set_theme", "forest")
	var screen: Control = load("res://src/screens/SSettings.tscn").instantiate()
	get_root().add_child(screen)
	await _test.wait_frames(self, 3)

	var res_720: Button = screen.get_node("MainMargin/Root/SettingsPanel/SettingsScroll/PanelContent/ResolutionRow/Btn720p")
	var res_1080: Button = screen.get_node("MainMargin/Root/SettingsPanel/SettingsScroll/PanelContent/ResolutionRow/Btn1080p")
	var res_max: Button = screen.get_node("MainMargin/Root/SettingsPanel/SettingsScroll/PanelContent/ResolutionRow/BtnMax")
	var quality_low: Button = screen.get_node("MainMargin/Root/SettingsPanel/SettingsScroll/PanelContent/QualityRow/BtnLowQuality")
	var quality_high: Button = screen.get_node("MainMargin/Root/SettingsPanel/SettingsScroll/PanelContent/QualityRow/BtnHighQuality")

	res_720.pressed.emit()
	_test.equal(_settings.get("resolution"), "720p", "Settings button applies the 720p resolution")
	res_1080.pressed.emit()
	_test.equal(_settings.get("resolution"), "1080p", "Settings button applies the 1080p resolution")
	res_max.pressed.emit()
	_test.equal(_settings.get("resolution"), "maximized", "Settings button applies maximized resolution")
	quality_low.pressed.emit()
	_test.equal(_settings.get("graphics_quality"), "low", "Settings button applies low graphics quality")
	quality_high.pressed.emit()
	_test.equal(_settings.get("graphics_quality"), "high", "Settings button applies high graphics quality")

	_settings.set("theme", "forest")
	_theme_manager.call("set_theme", "forest")
	var original_preview_theme := str(_theme_manager.get("current_theme_name"))
	var original_saved_theme := str(_settings.get("theme"))
	var original_index_text: String = screen.get_node("MainMargin/Root/SettingsPanel/SettingsScroll/PanelContent/ThemeCarousel/ThemeIndexLabel").text
	for _index in range(3):
		screen.call("_on_carousel_next")
		if str(_theme_manager.get("current_theme_name")) != original_preview_theme:
			break
	_test.expect(
		screen.get_node("MainMargin/Root/SettingsPanel/SettingsScroll/PanelContent/ThemeCarousel/ThemeIndexLabel").text != original_index_text
			or str(_theme_manager.get("current_theme_name")) != original_preview_theme,
		"Settings carousel previews a different theme"
	)
	_test.equal(_settings.get("theme"), original_saved_theme, "Theme preview does not persist before Apply")
	screen.call("_on_carousel_apply")
	_test.equal(_settings.get("theme"), _theme_manager.get("current_theme_name"), "Apply persists the previewed theme")

	if is_instance_valid(screen):
		screen.queue_free()
	await _test.wait_frames(self, 2)
	_settings.set("theme", "forest")
	_theme_manager.call("set_theme", "forest")
	var back_screen: Control = load("res://src/screens/SSettings.tscn").instantiate()
	get_root().add_child(back_screen)
	await _test.wait_frames(self, 3)
	var back_original := str(_theme_manager.get("current_theme_name"))
	back_screen.call("_on_carousel_next")
	back_screen.call("_on_back")
	_test.equal(_theme_manager.get("current_theme_name"), back_original, "Back restores the theme active when settings opened")
	back_screen.queue_free()
	await _test.wait_frames(self, 2)


func _restore_settings() -> void:
	_settings.set("theme", _original_theme)
	_settings.set("graphics_quality", _original_quality)
	_settings.set("resolution", _original_resolution)
	_settings.set("last_server_url", _original_last_url)
	_settings.set("last_library_name", _original_last_name)
	_theme_manager.call("set_theme", _original_theme)
	if _original_user_file.is_empty():
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SETTINGS_SCRIPT.SETTINGS_FILE))
	else:
		var restored := FileAccess.open(SETTINGS_SCRIPT.SETTINGS_FILE, FileAccess.WRITE)
		if restored != null:
			restored.store_string(_original_user_file)
			restored.close()
