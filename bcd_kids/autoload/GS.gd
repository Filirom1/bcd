# Autoload "GS" - Global State
extends Node

# API Configuration
# Empty by default - must be set by selecting a server in SServerDiscovery
var base_url := ""
var library_name := ""  # Friendly name (library_code) shown to users

# Data stores
var classes := []
var current_class := {}
var current_borrower := {}
var current_loans := []
var current_holds := []
var reserved_biblio_ids: Dictionary = {}  # IDs réservés cette session

# Settings loaded from API at startup
var settings := {}

# Configurable filters (parsed from settings CSV)
var filter_medium_types := []  # ["Livre", "BD", "Album", ...]
var filter_levels := []         # ["CP", "CE1", "CE2", ...]

func reset_borrower():
	current_borrower = {}
	current_loans = []
	current_holds = []
	reserved_biblio_ids = {}

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
