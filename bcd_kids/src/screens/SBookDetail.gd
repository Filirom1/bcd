# Screen: Book Detail — shown from search
extends Control

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _cover_img: TextureRect = %CoverImage
@onready var _no_cover_lbl: Label = %NoCoverLabel
@onready var _fields_container: VBoxContainer = %FieldsContainer
@onready var _http: HTTPRequest = %CoverHTTP

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_back_btn.pressed.connect(func(): Mgr.pop())
	_back_btn.call_deferred("grab_focus")

	var book: Dictionary = GS.current_class.get("_temp_book_data", {})
	_build_fields(book)

	var biblio_id := int(book.get("id", 0))
	if biblio_id > 0:
		var record = await API.get_bibliographic_record(biblio_id)
		if not record.has("error"):
			for key in ["shelf_location", "call_number"]:
				if record.get(key) == null and book.get(key) != null:
					record[key] = book[key]
			_build_fields(record)
			var cover_file: String = str(record.get("cover_image", "")) if record.get("cover_image") != null else ""
			if not cover_file.is_empty():
				_load_cover(cover_file)
				return
	_show_no_cover()

func _build_fields(data: Dictionary) -> void:
	for c in _fields_container.get_children():
		c.queue_free()

	var field_defs := [
		["title",            "Titre"],
		["subtitle",         "Sous-titre"],
		["authors",          "Auteurs"],
		["illustrators",     "Illustrateurs"],
		["publisher",        "Éditeur"],
		["publication_year", "Année"],
		["collection",       "Collection"],
		["series_number",    "Numéro de série"],
		["genre",            "Genre"],
		["level",            "Niveau"],
		["medium_type",      "Type"],
		["page_count",       "Pages"],
		["keywords",         "Mots-clés"],
		["description",      "Résumé"],
	]

	for pair in field_defs:
		var key: String = pair[0]
		var label: String = pair[1]
		var value = data.get(key, null)
		if value == null:
			continue
		if value is Array:
			if value.is_empty():
				continue
			value = ", ".join(value)
		elif value is int or value is float:
			if value == 0:
				continue
			value = str(value)
		else:
			value = str(value).strip_edges()
			if value.is_empty():
				continue

		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		_fields_container.add_child(row)

		var key_lbl := Label.new()
		key_lbl.text = label + " :"
		key_lbl.theme_type_variation = "LabelSmall"
		key_lbl.custom_minimum_size = Vector2(130, 0)
		row.add_child(key_lbl)

		var val_lbl := Label.new()
		val_lbl.text = str(value)
		val_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		val_lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		row.add_child(val_lbl)

	# Shelf location and call number — rendered with colored badges at the bottom
	var _sl = data.get("shelf_location")
	var _cn = data.get("call_number")
	var shelf: String = (str(_sl) if _sl != null else "").strip_edges()
	var call_num: String = (str(_cn) if _cn != null else "").strip_edges()
	if not shelf.is_empty() or not call_num.is_empty():
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		_fields_container.add_child(row)

		var key_lbl := Label.new()
		key_lbl.text = I18n.t("book_detail.location_label") + " :"
		key_lbl.theme_type_variation = "LabelSmall"
		key_lbl.custom_minimum_size = Vector2(130, 0)
		row.add_child(key_lbl)

		var badges := HBoxContainer.new()
		badges.add_theme_constant_override("separation", 4)
		row.add_child(badges)
		BadgeHelper.populate_badges(badges, shelf, call_num)

func _load_cover(filename: String) -> void:
	var url := API.get_cover_url(filename)
	_http.request_completed.connect(_on_cover_loaded)
	var err := _http.request(url)
	if err != OK:
		_show_no_cover()

func _on_cover_loaded(result: int, status: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or status < 200 or status >= 300:
		_show_no_cover()
		return
	var img := Image.new()
	var err := img.load_jpg_from_buffer(body)
	if err != OK:
		err = img.load_png_from_buffer(body)
	if err != OK:
		_show_no_cover()
		return
	_cover_img.texture = ImageTexture.create_from_image(img)
	_cover_img.visible = true
	_no_cover_lbl.visible = false

func _show_no_cover() -> void:
	_cover_img.visible = false
	_no_cover_lbl.visible = true

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		Mgr.pop()
		get_viewport().set_input_as_handled()
