# Loan Card Component
class_name LoanCard
extends PanelContainer

signal return_clicked(item_id: String)
signal renew_clicked(item_id: String)
signal title_clicked(loan: Dictionary)

@onready var _cover_img: TextureRect = %CoverImage
@onready var _cover_placeholder: Label = %CoverPlaceholder
@onready var _title_lbl: Label = %TitleLabel
@onready var _authors_lbl: Label = %AuthorsLabel
@onready var _due_lbl: Label = %DueLabel
@onready var _renew_btn: Button = %RenewBtn
@onready var _return_btn: Button = %ReturnBtn
@onready var _http: HTTPRequest = %CoverHTTP

var _loan_data: Dictionary

func setup(loan: Dictionary) -> void:
	_loan_data = loan
	var item_id: String = loan.get("item_id", "")
	var is_overdue: bool = loan.get("is_overdue", false)
	var due_date: String = loan.get("due_date", "")

	_title_lbl.text = loan.get("display_title", loan.get("title", ""))

	var authors = loan.get("authors", [])
	var authors_text: String
	if authors is Array:
		authors_text = ", ".join(authors) if not authors.is_empty() else ""
	else:
		authors_text = str(authors) if authors != null else ""
	if authors_text.is_empty():
		authors_text = loan.get("publisher", "")
	_authors_lbl.text = authors_text
	_authors_lbl.visible = not _authors_lbl.text.is_empty()

	if is_overdue:
		_due_lbl.text = "⚠️ " + I18n.t("main_menu.overdue") + ": " + due_date
		_due_lbl.theme_type_variation = "LabelError"
		theme_type_variation = "PanelError"
	else:
		_due_lbl.text = "⏰ " + due_date
		_due_lbl.theme_type_variation = "LabelSubtitle"
		theme_type_variation = "PanelSuccess"

	_renew_btn.text = "🔄 " + "Renouveler"
	_renew_btn.pressed.connect(func(): renew_clicked.emit(item_id))
	
	# Cover thumbnail — click opens cover screen
	var cover_file: String = loan.get("cover_image", "") if loan.get("cover_image") != null else ""
	if not cover_file.is_empty():
		_load_cover(cover_file)
	else:
		_show_placeholder()

	_cover_img.gui_input.connect(func(event):
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			title_clicked.emit(_loan_data)
	)
	_cover_placeholder.gui_input.connect(func(event):
		if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
			title_clicked.emit(_loan_data)
	)

func _load_cover(filename: String) -> void:
	var url := API.get_cover_url(filename)
	_http.request_completed.connect(_on_cover_loaded)
	var err := _http.request(url)
	if err != OK:
		_show_placeholder()

func _on_cover_loaded(result: int, status: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS or status < 200 or status >= 300:
		_show_placeholder()
		return
	var img := Image.new()
	var err := img.load_jpg_from_buffer(body)
	if err != OK:
		err = img.load_png_from_buffer(body)
	if err != OK:
		_show_placeholder()
		return
	_cover_img.texture = ImageTexture.create_from_image(img)
	_cover_img.visible = true
	_cover_placeholder.visible = false

func _show_placeholder() -> void:
	_cover_img.visible = false
	_cover_placeholder.visible = true
