extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")

var _test := SUPPORT.new()


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	await _test_autocomplete()
	await _test_breadcrumb()
	await _test_class_button()
	await _test_filter_panel()
	await _test_notification()
	await _test_server_card()
	await _test_book_card()
	await _test_hold_card()
	await _test_loan_card()
	_test.finish(self)


func _test_autocomplete() -> void:
	var input = load("res://src/components/AutocompleteInput.tscn").instantiate()
	get_root().add_child(input)
	await _test.wait_frames(self)
	var line_edit: LineEdit = input.get_node("SearchInput")
	var submitted: Array = []
	input.search_submitted.connect(func(query): submitted.append(query))
	input.set_placeholder("Search books")
	line_edit.text = "dragon"
	_test.equal(input.get_text(), "dragon", "Autocomplete returns the current input text")
	_test.equal(line_edit.placeholder_text, "Search books", "Autocomplete sets its placeholder")
	input.call("_on_text_submitted", "dragon")
	_test.equal(submitted, ["dragon"], "Autocomplete emits submitted searches")
	input.clear()
	_test.equal(input.get_text(), "", "Autocomplete clears the input")
	input.focus_input()
	await _test.wait_frames(self)
	_test.expect(input.is_input_focused(), "Autocomplete focuses its line edit")
	input.queue_free()
	await _test.wait_frames(self)


func _test_breadcrumb() -> void:
	var breadcrumb = load("res://src/components/Breadcrumb.tscn").instantiate()
	get_root().add_child(breadcrumb)
	await _test.wait_frames(self)
	var clicked: Array = []
	breadcrumb.crumb_clicked.connect(func(screen): clicked.append(screen))
	breadcrumb.set_path([
		{"text": "Library", "screen": "class_select", "clickable": true},
		{"text": "CP", "screen": "name_input", "clickable": true},
		{"text": "Alice", "screen": "", "clickable": false},
	])
	await _test.wait_frames(self)
	_test.equal(breadcrumb.get_child_count(), 5, "Breadcrumb creates buttons, separators, and the final label")
	_test.expect(breadcrumb.get_child(0) is Button, "Breadcrumb uses a button for clickable crumbs")
	_test.expect(breadcrumb.get_child(2) is Button, "Breadcrumb keeps intermediate crumbs clickable")
	_test.expect(breadcrumb.get_child(4) is Label, "Breadcrumb uses a label for the final crumb")
	(breadcrumb.get_child(0) as Button).pressed.emit()
	_test.equal(clicked, ["class_select"], "Breadcrumb emits the selected screen")
	breadcrumb.set_path([])
	await _test.wait_frames(self)
	_test.equal(breadcrumb.get_child_count(), 0, "Breadcrumb clears its path")
	breadcrumb.queue_free()
	await _test.wait_frames(self)


func _test_class_button() -> void:
	var button = load("res://src/components/ClassButton.tscn").instantiate()
	get_root().add_child(button)
	await _test.wait_frames(self)
	var selected: Array = []
	button.class_selected.connect(func(cls): selected.append(cls))
	button.setup({"id": 3, "name": "CE1", "homeroom_teacher": "Mme Dupont"})
	_test.equal(button.get_node("Content/ClassNameLabel").text, "CE1", "Class button displays the class name")
	_test.equal(button.get_node("Content/TeacherLabel").text, "👨‍🏫 Mme Dupont", "Class button displays the teacher")
	_test.expect(button.get_node("Content/TeacherLabel").visible, "Class button shows a non-empty teacher")
	button.call("_pressed")
	_test.equal(selected, [{"id": 3, "name": "CE1", "homeroom_teacher": "Mme Dupont"}], "Class button emits its class data")
	button.setup({"name": "CP"})
	_test.equal(button.get_node("Content/TeacherLabel").text, "", "Class button clears a missing teacher")
	_test.expect(not button.get_node("Content/TeacherLabel").visible, "Class button hides a missing teacher")
	button.queue_free()
	await _test.wait_frames(self)


func _test_filter_panel() -> void:
	var panel = load("res://src/components/FilterPanel.tscn").instantiate()
	get_root().add_child(panel)
	await _test.wait_frames(self)
	var events: Array = []
	panel.filters_changed.connect(func(filters): events.append(filters))
	panel.setup(["Livre", "BD"])
	var type_option: OptionButton = panel.get_node("FiltersRow/TypeGroup/TypeOption")
	var available: CheckBox = panel.get_node("AvailableCheckbox")
	_test.equal(type_option.item_count, 3, "Filter panel includes All and each medium type")
	_test.equal(panel.get_filters(), {}, "Filter panel starts with no active filters")
	type_option.select(2)
	panel.call("_on_filter_changed")
	_test.equal(panel.get_filters(), {"medium_type": "BD"}, "Filter panel returns the selected medium type")
	available.button_pressed = true
	panel.call("_on_filter_changed")
	_test.equal(
		panel.get_filters(),
		{"medium_type": "BD", "available_only": true},
		"Filter panel combines medium and availability filters"
	)
	_test.expect(events.size() >= 2, "Filter panel emits filter changes")
	panel.queue_free()
	await _test.wait_frames(self)


func _test_notification() -> void:
	var notification = load("res://src/components/Notification.tscn").instantiate()
	get_root().add_child(notification)
	await _test.wait_frames(self)
	var label: Label = notification.get_node("MessageLabel")
	for notification_type in ["success", "error", "warning", "other"]:
		notification.setup("Message", notification_type)
		_test.equal(label.text, "Message", "Notification displays its message: " + notification_type)
	_test.equal(notification.theme_type_variation, "PanelNotificationSuccess", "Notification defaults unknown types to success")
	notification.queue_free()
	await _test.wait_frames(self)


func _test_server_card() -> void:
	var card = load("res://src/components/ServerCard.tscn").instantiate()
	get_root().add_child(card)
	await _test.wait_frames(self)
	var connections: Array = []
	var admins: Array = []
	card.connect_pressed.connect(func(url, name): connections.append([url, name]))
	card.admin_pressed.connect(func(url): admins.append(url))
	card.setup({
		"library_code": "BCD Paris",
		"url": "http://127.0.0.1:8888/api/v1/",
		"host": "127.0.0.1",
	}, true)
	_test.equal(card.get_node("Row/Info/NameLabel").text, "📚 BCD Paris", "Server card displays the library name")
	_test.equal(card.get_node("Row/Info/HostLabel").text, "127.0.0.1", "Server card displays the host")
	_test.expect(card.get_node("Row/Info/HostLabel").visible, "Server card shows a non-empty host")
	card.get_node("Row/ConnectBtn").pressed.emit()
	card.get_node("Row/AdminBtn").pressed.emit()
	_test.equal(connections, [["http://127.0.0.1:8888/api/v1/", "BCD Paris"]], "Server card emits connection details")
	_test.equal(admins, ["http://127.0.0.1:8888"], "Server card emits the web admin URL")
	card.queue_free()
	await _test.wait_frames(self)


func _test_book_card() -> void:
	var available = load("res://src/components/BookCard.tscn").instantiate()
	get_root().add_child(available)
	await _test.wait_frames(self)
	var actions: Array = []
	var details: Array = []
	available.action_clicked.connect(func(data): actions.append(data))
	available.detail_clicked.connect(func(data): details.append(data))
	var book := {
		"id": 5,
		"title": "The Dragon",
		"authors": ["A. Writer", "B. Artist"],
		"available_copies": 2,
		"shelf_location": "Romans",
		"call_number": "843",
	}
	available.setup(book, "Reserve", Color("#123456"))
	_test.equal(available.get_node("Content/TitleLabel").text, "The Dragon", "Book card displays the title")
	_test.equal(available.get_node("Content/AuthorsLabel").text, "A. Writer, B. Artist", "Book card joins authors")
	_test.equal(available.get_node("Content/StatusRow/StatusLabel").text, "🟢", "Book card marks available books")
	var nullable_book: Control = load("res://src/components/BookCard.tscn").instantiate()
	var i18n: Node = get_root().get_node("I18n")
	get_root().add_child(nullable_book)
	await _test.wait_frames(self)
	nullable_book.setup({"title": null, "publisher": null, "authors": [], "available_copies": 0}, "", Color.WHITE)
	_test.equal(nullable_book.get_node("Content/TitleLabel").text, i18n.call("t", "common.unknown_title"), "Book card handles a null title")
	_test.equal(nullable_book.get_node("Content/AuthorsLabel").text, "", "Book card handles a null publisher")
	nullable_book.queue_free()
	await _test.wait_frames(self)
	_test.expect(available.get_node("Content/BtnRow/ActionBtn").visible, "Book card shows a non-empty action")
	available.call("grab_first_focus")
	available.get_node("Content/BtnRow/ActionBtn").pressed.emit()
	available.get_node("Content/BtnRow/DetailBtn").pressed.emit()
	_test.equal(actions, [book], "Book card emits action data")
	_test.equal(details, [book], "Book card emits detail data")
	available.queue_free()
	await _test.wait_frames(self)

	var held = load("res://src/components/BookCard.tscn").instantiate()
	get_root().add_child(held)
	await _test.wait_frames(self)
	held.setup({"title": "Held", "authors": [], "publisher": "Publisher", "available_copies": 0, "active_holds_count": 2}, "", Color.WHITE)
	held.call("grab_first_focus")
	_test.equal(held.get_node("Content/AuthorsLabel").text, "Publisher", "Book card falls back to publisher")
	_test.equal(held.get_node("Content/StatusRow/StatusLabel").text, "🟡", "Book card marks books with holds")
	_test.expect(not held.get_node("Content/BtnRow/ActionBtn").visible, "Book card hides an empty action")
	held.queue_free()
	await _test.wait_frames(self)

	var unavailable = load("res://src/components/BookCard.tscn").instantiate()
	get_root().add_child(unavailable)
	await _test.wait_frames(self)
	unavailable.setup({"title": "Unavailable", "authors": [], "available_copies": 0}, "", Color.WHITE)
	_test.equal(unavailable.get_node("Content/StatusRow/StatusLabel").text, "🔴", "Book card marks unavailable books")
	unavailable.queue_free()
	await _test.wait_frames(self)


func _test_hold_card() -> void:
	var ready = load("res://src/components/HoldCard.tscn").instantiate()
	get_root().add_child(ready)
	await _test.wait_frames(self)
	var cancelled: Array = []
	ready.cancel_clicked.connect(func(hold_id): cancelled.append(hold_id))
	ready.setup({"id": 12, "title": "Ready", "authors": ["Author"], "status": "ready", "expiration_date": "2026-06-30"})
	ready.call("grab_first_focus")
	_test.equal(ready.get_node("Row/Info/TitleLabel").text, "Ready", "Hold card displays a title")
	_test.expect(ready.get_node("Row/Info/AuthorsLabel").visible, "Hold card displays authors when present")
	_test.expect(ready.get_node("Row/Info/ExpiresLabel").visible, "Ready hold displays its expiration date")
	ready.get_node("Row/CancelBtn").pressed.emit()
	_test.equal(cancelled, [12], "Hold card emits its hold ID")
	ready.queue_free()
	await _test.wait_frames(self)

	var queued = load("res://src/components/HoldCard.tscn").instantiate()
	get_root().add_child(queued)
	await _test.wait_frames(self)
	queued.setup({"id": 13, "title": "Queued", "authors": [], "status": "pending", "queue_position": 3})
	_test.expect(not queued.get_node("Row/Info/AuthorsLabel").visible, "Hold card hides missing authors")
	_test.expect(queued.theme_type_variation == "PanelInfo", "Queued hold uses the information panel variation")
	queued.queue_free()
	await _test.wait_frames(self)


func _test_loan_card() -> void:
	var loan_card = load("res://src/components/LoanCard.tscn").instantiate()
	get_root().add_child(loan_card)
	await _test.wait_frames(self)
	var renewed: Array = []
	var opened: Array = []
	loan_card.renew_clicked.connect(func(item_id): renewed.append(item_id))
	loan_card.title_clicked.connect(func(loan): opened.append(loan))
	var loan := {
		"item_id": "A-1",
		"display_title": "Loaned Book",
		"authors": ["Author"],
		"due_date": "2026-07-01",
		"is_overdue": false,
	}
	loan_card.setup(loan)
	_test.equal(loan_card.get_node("Row/Info/TitleLabel").text, "Loaned Book", "Loan card displays the loan title")
	loan_card.setup({"item_id": "A-null", "display_title": null, "title": null, "authors": [], "publisher": null, "due_date": null})
	_test.equal(loan_card.get_node("Row/Info/TitleLabel").text, "", "Loan card handles null title fields")
	_test.equal(loan_card.get_node("Row/Info/DueLabel").text, "⏰ ", "Loan card handles a null due date")
	loan_card.setup(loan)
	_test.equal(loan_card.get_node("Row/Info/DueLabel").text, "⏰ 2026-07-01", "Loan card displays an on-time due date")
	_test.expect(loan_card.get_node("Row/CoverZone/CoverPlaceholder").visible, "Loan card shows a placeholder without a cover")
	loan_card.get_node("Row/BtnRow/RenewBtn").pressed.emit()
	_test.equal(renewed, ["A-1"], "Loan card emits a renewal request")
	_test.expect(loan_card.get_node_or_null("Row/BtnRow/ReturnBtn") == null, "Loan card has no direct return button")
	var cover: CoverImage = loan_card.get_node("Row/CoverZone/CoverImage")
	var cover_texture := CoverImage.texture_from_response(HTTPRequest.RESULT_SUCCESS, 200, _tiny_jpg())
	cover.texture = cover_texture
	loan_card.call("_on_cover_texture_loaded", cover_texture)
	_test.expect(cover.visible, "Loan card accepts a valid cover")
	loan_card.get_node("Row/CoverZone/CoverImage").gui_input.emit(_left_click())
	_test.equal(opened, [loan], "Loan card emits the loan when its cover is clicked")
	loan_card.queue_free()
	await _test.wait_frames(self)

	var overdue = load("res://src/components/LoanCard.tscn").instantiate()
	get_root().add_child(overdue)
	await _test.wait_frames(self)
	overdue.setup({"item_id": "A-2", "title": "Late Book", "authors": "Single Author", "publisher": "Publisher", "due_date": "2026-01-01", "is_overdue": true, "cover_image": "missing.jpg"})
	_test.expect(overdue.get_node("Row/Info/DueLabel").text.begins_with("⚠️"), "Loan card marks an overdue loan")
	_test.equal(overdue.get_node("Row/Info/AuthorsLabel").text, "Single Author", "Loan card accepts a scalar author value")
	overdue.call("_on_cover_failed")
	_test.expect(overdue.get_node("Row/CoverZone/CoverPlaceholder").visible, "Loan card falls back when cover loading fails")
	overdue.queue_free()
	await _test.wait_frames(self)


func _left_click() -> InputEventMouseButton:
	var event := InputEventMouseButton.new()
	event.pressed = true
	event.button_index = MOUSE_BUTTON_LEFT
	return event


func _tiny_jpg() -> PackedByteArray:
	var image := Image.create(2, 2, false, Image.FORMAT_RGB8)
	image.fill(Color("#ff0000"))
	return image.save_jpg_to_buffer()
