# A single returned-book entry shown by the return screen.
class_name HistoryEntry
extends VBoxContainer

@onready var _status_label: Label = %StatusLabel
@onready var _location_row: HBoxContainer = %LocationRow
@onready var _location_label: Label = %LocationLabel
@onready var _badges: HBoxContainer = %Badges

func setup(
	title: String,
	borrower_name: String,
	was_late: bool,
	days_overdue: int,
	shelf: String,
	call_number: String
) -> void:
	var status_text := I18n.t("return.late", {"days": days_overdue}) if was_late else I18n.t("return.on_time")
	var icon := "⚠️" if was_late else "✅"
	_status_label.text = "%s %s · %s · %s" % [icon, title, borrower_name, status_text]
	_location_label.text = I18n.t("return.ranger_a")
	_location_row.visible = not shelf.is_empty() or not call_number.is_empty()
	if _location_row.visible:
		BadgeHelper.populate_badges(_badges, shelf, call_number)
