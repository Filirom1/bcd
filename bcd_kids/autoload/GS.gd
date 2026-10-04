# Autoload "GS" - Global State
extends Node

# API Configuration
# Empty by default - must be set by selecting a server in SServerDiscovery
var base_url := ""
var library_name := ""  # Friendly name (library_code) shown to users

# Data stores
var current_class := {}
var current_borrower := {}
var current_loans := []
var current_holds := []

# One-shot values passed between screens. Server data remains in the dedicated
# stores above; navigation data does not get mixed into current_class.
var nav_params: Dictionary = {}

# Settings loaded from API at startup
var settings := {}

# Configurable filters (parsed from settings CSV)
var filter_medium_types := []  # ["Livre", "BD", "Album", ...]

func reset_borrower() -> void:
	current_borrower = {}
	current_loans = []
	current_holds = []
	nav_params.clear()

func set_nav_param(key: String, value) -> void:
	nav_params[key] = value

func get_nav_param(key: String, default_value = null):
	return nav_params.get(key, default_value)

func take_nav_param(key: String, default_value = null):
	var value = nav_params.get(key, default_value)
	nav_params.erase(key)
	return value

func clear_nav_param(key: String) -> void:
	nav_params.erase(key)

func clear_nav_params() -> void:
	nav_params.clear()

func parse_csv_list(csv: String) -> Array:
	if not csv:
		return []
	var items = csv.split(",")
	var result = []
	for item in items:
		var trimmed = item.strip_edges()
		if trimmed:
			result.append(trimmed)
	return result
