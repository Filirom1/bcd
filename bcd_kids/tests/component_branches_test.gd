extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")

var _test := SUPPORT.new()


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	await _test_focus_styles()
	await _test_repeated_setup_signals()
	await _test_cover_decode_fallbacks()
	_test.finish(self)


func _test_focus_styles() -> void:
	var card = load("res://src/components/BookCard.tscn").instantiate()
	get_root().add_child(card)
	await _test.wait_frames(self, 2)
	var action: Button = card.get_node("Content/Info/BtnRow/ActionBtn")
	action.focus_entered.emit()
	_test.expect(action.has_theme_stylebox_override("normal"), "Book card applies its focus style on focus enter")
	action.focus_exited.emit()
	_test.expect(not action.has_theme_stylebox_override("normal"), "Book card removes its focus style on focus exit")
	card.queue_free()
	await _test.wait_frames(self, 2)

	var loan = load("res://src/components/LoanCard.tscn").instantiate()
	get_root().add_child(loan)
	await _test.wait_frames(self, 2)
	var renew: Button = loan.get_node("Row/BtnRow/RenewBtn")
	renew.focus_entered.emit()
	_test.expect(renew.has_theme_stylebox_override("normal"), "Loan card applies its focus style")
	renew.focus_exited.emit()
	_test.expect(not renew.has_theme_stylebox_override("normal"), "Loan card removes its focus style")
	loan.queue_free()
	await _test.wait_frames(self, 2)


func _test_repeated_setup_signals() -> void:
	var book_card = load("res://src/components/BookCard.tscn").instantiate()
	get_root().add_child(book_card)
	await _test.wait_frames(self, 2)
	var book_events: Array = []
	book_card.action_clicked.connect(func(data): book_events.append(data))
	book_card.detail_clicked.connect(func(data): book_events.append({"detail": data}))
	var first_book := {"id": 1, "title": "First", "available_copies": 1}
	var second_book := {"id": 2, "title": "Second", "available_copies": 1}
	book_card.setup(first_book, "Reserve", Color.WHITE)
	book_card.setup(second_book, "Reserve", Color.WHITE)
	book_card.get_node("Content/Info/BtnRow/ActionBtn").pressed.emit()
	book_card.get_node("Content/Info/BtnRow/DetailBtn").pressed.emit()
	_test.equal(book_events.size(), 2, "Book card setup does not duplicate action or detail signal handlers")
	if book_events.size() == 2:
		_test.equal(book_events[0], second_book, "Book card action uses the most recent setup data")
		_test.equal(book_events[1], {"detail": second_book}, "Book card detail uses the most recent setup data")
	book_card.queue_free()
	await _test.wait_frames(self, 2)

	var loan_card = load("res://src/components/LoanCard.tscn").instantiate()
	get_root().add_child(loan_card)
	await _test.wait_frames(self, 2)
	var renew_events: Array = []
	loan_card.renew_clicked.connect(func(item_id): renew_events.append(item_id))
	loan_card.setup({"item_id": "A-1", "display_title": "First"})
	loan_card.setup({"item_id": "B-2", "display_title": "Second"})
	loan_card.get_node("Row/BtnRow/RenewBtn").pressed.emit()
	_test.equal(renew_events, ["B-2"], "Loan card setup keeps one renewal handler and uses current data")
	loan_card.queue_free()
	await _test.wait_frames(self, 2)

	var hold_card = load("res://src/components/HoldCard.tscn").instantiate()
	get_root().add_child(hold_card)
	await _test.wait_frames(self, 2)
	var cancel_events: Array = []
	hold_card.cancel_clicked.connect(func(hold_id): cancel_events.append(hold_id))
	hold_card.setup({"id": 4, "title": "First", "status": "pending", "queue_position": 1})
	hold_card.setup({"id": 5, "title": "Second", "status": "pending", "queue_position": 2})
	hold_card.get_node("Row/CancelBtn").pressed.emit()
	_test.equal(cancel_events, [5], "Hold card setup keeps one cancellation handler and uses current data")
	hold_card.queue_free()
	await _test.wait_frames(self, 2)

	var server_card = load("res://src/components/ServerCard.tscn").instantiate()
	get_root().add_child(server_card)
	await _test.wait_frames(self, 2)
	var connection_events: Array = []
	server_card.connect_pressed.connect(func(url, name): connection_events.append([url, name]))
	server_card.setup({"url": "http://first/api/v1", "library_code": "First", "host": "first"})
	server_card.setup({"url": "http://second/api/v1", "library_code": "Second", "host": "second"})
	server_card.get_node("Row/ConnectBtn").pressed.emit()
	_test.equal(connection_events, [["http://second/api/v1", "Second"]], "Server card setup keeps one connection handler")
	server_card.queue_free()
	await _test.wait_frames(self, 2)


func _test_cover_decode_fallbacks() -> void:
	var image: Image = _image()
	var jpg := image.save_jpg_to_buffer()
	var png := image.save_png_to_buffer()
	var detail: Control = load("res://src/screens/SBookDetail.tscn").instantiate()
	get_root().add_child(detail)
	await _test.wait_frames(self, 2)
	var cover: CoverImage = detail.get_node("MainMargin/Root/Body/CoverCol/CoverImage")
	var jpg_texture := CoverImage.texture_from_response(HTTPRequest.RESULT_SUCCESS, 200, jpg)
	cover.texture = jpg_texture
	detail.call("_on_cover_texture_loaded", jpg_texture)
	_test.expect(cover.visible, "Book detail accepts valid JPEG data")
	var png_texture := CoverImage.texture_from_response(HTTPRequest.RESULT_SUCCESS, 200, png)
	cover.texture = png_texture
	detail.call("_on_cover_texture_loaded", png_texture)
	_test.expect(cover.visible, "Book detail accepts valid PNG data")
	_test.expect(CoverImage.texture_from_buffer(PackedByteArray()) == null, "Cover image decoder rejects invalid image data")
	detail.call("_show_no_cover")
	_test.expect(detail.get_node("MainMargin/Root/Body/CoverCol/NoCoverLabel").visible, "Book detail shows a placeholder for invalid image data")
	detail.queue_free()
	await _test.wait_frames(self, 2)


func _image() -> Image:
	var image := Image.create(2, 2, false, Image.FORMAT_RGB8)
	image.fill(Color("#44aaff"))
	return image
