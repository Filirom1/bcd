# Reusable empty/error message displayed inside a list or grid.
class_name EmptyState
extends Label

func setup(message: String, alignment: HorizontalAlignment = HORIZONTAL_ALIGNMENT_CENTER) -> void:
	text = message
	horizontal_alignment = alignment
