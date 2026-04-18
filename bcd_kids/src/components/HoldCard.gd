# Hold Card Component
class_name HoldCard
extends PanelContainer

signal cancel_clicked(hold_id: int)

@onready var _title_lbl: Label = %TitleLabel
@onready var _authors_lbl: Label = %AuthorsLabel
@onready var _status_lbl: Label = %StatusLabel
@onready var _expires_lbl: Label = %ExpiresLabel
@onready var _cancel_btn: Button = %CancelBtn

func setup(hold: Dictionary) -> void:
	var hold_id: int = hold.get("id", 0)
	var status: String = hold.get("status", "")

	_title_lbl.text = hold.get("title", "")

	var authors = hold.get("authors", [])
	_authors_lbl.text = ", ".join(authors) if authors is Array and not authors.is_empty() else ""
	_authors_lbl.visible = not _authors_lbl.text.is_empty()

	if status == "ready":
		_status_lbl.text = "✨ " + I18n.t("hold.available")
		_status_lbl.theme_type_variation = "LabelSuccess"
		var expires: String = hold.get("expiration_date", "")
		if expires:
			_expires_lbl.text = I18n.t("hold.expires", {"date": expires})
			_expires_lbl.theme_type_variation = "LabelSubtitle"
			_expires_lbl.visible = true
		theme_type_variation = "PanelWarning"
	else:
		var queue_pos: int = hold.get("queue_position", 0)
		_status_lbl.text = I18n.t("hold.position", {"position": queue_pos})
		_status_lbl.theme_type_variation = "LabelWarning"
		theme_type_variation = "PanelInfo"

	_cancel_btn.text = I18n.t("hold.cancel")
	_cancel_btn.add_theme_color_override("font_color", ThemeManager.ERROR)
	_cancel_btn.pressed.connect(func(): cancel_clicked.emit(hold_id))
