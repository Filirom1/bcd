# Screen: Book Cover — shown when tapping a loan title
extends Control

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _cover_img: TextureRect = %CoverImage
@onready var _title_lbl: Label = %TitleLabel
@onready var _authors_lbl: Label = %AuthorsLabel
@onready var _due_lbl: Label = %DueLabel
@onready var _no_cover_lbl: Label = %NoCoverLabel
@onready var _http: HTTPRequest = %CoverHTTP

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_back_btn.pressed.connect(func(): Mgr.pop())

	var loan: Dictionary = GS.current_class.get("_temp_loan_for_cover", {})
	_title_lbl.text = loan.get("display_title", loan.get("title", ""))

	var authors = loan.get("authors", [])
	var authors_text := ", ".join(authors) if authors is Array and not authors.is_empty() else ""
	_authors_lbl.text = authors_text
	_authors_lbl.visible = not authors_text.is_empty()

	var due_date: String = loan.get("due_date", "")
	_due_lbl.text = "⏰ " + due_date if due_date else ""
	_due_lbl.visible = not due_date.is_empty()

	# Try to fetch bibliographic record to get cover_image filename
	var biblio_id := int(loan.get("bibliographic_record_id", 0))
	if biblio_id > 0:
		var record = await API.get_bibliographic_record(biblio_id)
		if not record.has("error"):
			var cover_file: String = str(record.get("cover_image", "")) if record.get("cover_image") != null else ""
			if not cover_file.is_empty():
				_load_cover(cover_file)
				return
	_show_no_cover()

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
