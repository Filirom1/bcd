extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")

var _test := SUPPORT.new()


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	var i18n: Node = get_root().get_node("I18n")
	var original_locale := str(i18n.get("current_locale"))
	var viewport_width := get_root().get_viewport().get_visible_rect().size.x

	for locale in ["en", "fr"]:
		i18n.call("set_locale", locale)
		var discovery: Control = load("res://src/screens/SServerDiscovery.tscn").instantiate()
		discovery.set("_discovering", true)
		get_root().add_child(discovery)
		await _test.wait_frames(self, 3)
		var title: Label = discovery.get_node("MainMargin/Root/TitleLabel")
		_test.equal(title.text, i18n.call("t", "server_discovery.title"), "Export locale initializes the discovery title: " + locale)
		_test.expect(
			title.get_combined_minimum_size().x <= viewport_width,
			"Export locale keeps the discovery title within the viewport: " + locale
		)
		var class_button: Control = load("res://src/components/ClassButton.tscn").instantiate()
		get_root().add_child(class_button)
		await _test.wait_frames(self)
		class_button.call("setup", {"name": "CE1", "homeroom_teacher": "Professeur 👨‍🏫"})
		_test.expect(
			class_button.get_node("Content/TeacherLabel").text.contains("👨‍🏫"),
			"Export keeps the teacher emoji text: " + locale
		)
		class_button.queue_free()
		discovery.queue_free()
		await _test.wait_frames(self, 2)

	i18n.call("set_locale", original_locale)
	_test.equal(
		ProjectSettings.get_setting("application/config/auto_accept_quit", true),
		false,
		"Export keeps the quit confirmation guard enabled"
	)

	var main: Node = load("res://main.tscn").instantiate()
	get_root().add_child(main)
	await _test.wait_frames(self, 2)
	var quit_dialog: ConfirmationDialog = main.get_node("QuitDialog")
	_test.expect(not quit_dialog.title.is_empty(), "Export initializes the quit dialog title")
	_test.expect(not quit_dialog.get_cancel_button().text.is_empty(), "Export initializes the quit cancel button")
	main.queue_free()
	await _test.wait_frames(self, 2)

	_test.finish(self)
