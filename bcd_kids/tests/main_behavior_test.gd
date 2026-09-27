extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")

var _test := SUPPORT.new()
var _i18n: Node


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	_i18n = get_root().get_node("I18n")
	var main: Node = load("res://main.tscn").instantiate()
	get_root().add_child(main)
	await _test.wait_frames(self, 3)
	var dialog: ConfirmationDialog = main.get_node("QuitDialog")

	_test.equal(dialog.title, _i18n.call("t", "quit.title"), "Quit dialog uses the translated title")
	_test.equal(dialog.dialog_text, _i18n.call("t", "quit.message"), "Quit dialog uses the translated message")
	_test.equal(dialog.get_ok_button().text, _i18n.call("t", "quit.confirm"), "Quit dialog labels the confirmation button")
	_test.equal(dialog.get_cancel_button().text, _i18n.call("t", "quit.cancel"), "Quit dialog labels the cancellation button")

	main.call("_on_window_close_requested")
	_test.expect(dialog.visible, "Window close opens the quit dialog")
	main.call("_on_window_close_requested")
	_test.expect(dialog.visible, "Repeated window close does not replace a visible dialog")

	# The confirmation signal is wired to the quit method without emitting it in
	# this process (emitting it would intentionally terminate the test runner).
	var confirmed_connections: Array = dialog.confirmed.get_connections()
	_test.expect(not confirmed_connections.is_empty(), "Quit dialog connects confirmation to application quit")
	if not confirmed_connections.is_empty():
		var callable: Callable = confirmed_connections[0].get("callable", Callable())
		_test.equal(callable.get_method(), "_quit_application", "Quit confirmation targets the quit handler")

	dialog.get_cancel_button().pressed.emit()
	await _test.wait_frames(self)
	_test.expect(not dialog.visible, "Cancelling the quit dialog closes it without quitting")
	main.queue_free()
	await _test.wait_frames(self, 2)
	_test.finish(self)
