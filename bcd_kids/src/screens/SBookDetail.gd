# Screen: Book Detail — shown from search
extends Control

const FIELD_ROW = preload("res://src/components/FieldRow.tscn")
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")
const DATA = preload("res://src/utils/DataHelper.gd")

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _cover_img: CoverImage = %CoverImage
@onready var _no_cover_lbl: Label = %NoCoverLabel
@onready var _fields_container: VBoxContainer = %FieldsContainer


func _ready() -> void:
	_bg.color = ThemeManager.BG
	_cover_img.cover_loaded.connect(_on_cover_texture_loaded)
	_cover_img.cover_failed.connect(_on_cover_failed)
	_back_btn.text = "← " + I18n.t("common.back")
	_back_btn.pressed.connect(_go_back)
	_back_btn.call_deferred("grab_focus")

	var book: Dictionary = GS.get_nav_param("book_data", {})
	_build_fields(book)

	var biblio_id := int(book.get("id", 0))
	var generation := Mgr.navigation_generation
	if biblio_id > 0:
		var record = await API.get_bibliographic_record(biblio_id)
		if not is_inside_tree() or not Mgr.is_generation_current(generation):
			return
		if record is Dictionary and not record.has("error"):
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
	NODE_HELPER.clear_children(_fields_container)

	var field_defs := [
		["title",            "book_detail.title"],
		["subtitle",         "book_detail.subtitle"],
		["authors",          "book_detail.authors"],
		["illustrators",     "book_detail.illustrators"],
		["publisher",        "book_detail.publisher"],
		["publication_year", "book_detail.publication_year"],
		["collection",       "book_detail.collection"],
		["series_number",    "book_detail.series_number"],
		["level",            "book_detail.level"],
		["medium_type",      "book_detail.medium_type"],
		["page_count",       "book_detail.page_count"],
		["keywords",         "book_detail.keywords"],
		["description",      "book_detail.description"],
	]

	for pair in field_defs:
		var key: String = pair[0]
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

		var row := FIELD_ROW.instantiate() as FieldRow
		_fields_container.add_child(row)
		row.setup(I18n.t(pair[1]), str(value))

	# Shelf location and call number are rendered with colored badges.
	var shelf := DATA.text(data, "shelf_location").strip_edges()
	var call_num := DATA.text(data, "call_number").strip_edges()
	if not shelf.is_empty() or not call_num.is_empty():
		var location_row := FIELD_ROW.instantiate() as FieldRow
		_fields_container.add_child(location_row)
		location_row.setup_location(I18n.t("book_detail.location_label"), shelf, call_num)

func _load_cover(filename: String) -> void:
	_cover_img.load_cover(filename)

func _on_cover_texture_loaded(_texture: Texture2D) -> void:
	_cover_img.visible = true
	_no_cover_lbl.visible = false

func _on_cover_failed() -> void:
	_show_no_cover()

func _show_no_cover() -> void:
	_cover_img.visible = false
	_no_cover_lbl.visible = true

func _go_back() -> void:
	GS.clear_nav_param("book_data")
	Mgr.pop()

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		_go_back()
		get_viewport().set_input_as_handled()
