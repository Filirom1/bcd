# Compact loan row used on the checkout screen.
class_name LoanSummary
extends Label

const DATA = preload("res://src/utils/DataHelper.gd")

func setup(loan: Dictionary) -> void:
	var display_title := DATA.display_title(loan)
	text = "✅ %s - %s" % [display_title, DATA.text(loan, "due_date")]
