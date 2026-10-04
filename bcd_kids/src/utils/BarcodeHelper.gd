# Barcode parsing shared by the student and teacher scan workflows.
class_name BarcodeHelper
extends RefCounted

static func configured_prefix(settings: Dictionary, key: String, default_value: String) -> String:
	var value = settings.get(key, default_value)
	return default_value if value == null else str(value).strip_edges()

static func clean(text: String) -> String:
	return text.strip_edges().replace(" ", "")

# Checkout and return screens accept raw item IDs as well as prefixed scans.
static func item_id(text: String, settings: Dictionary) -> String:
	var value := clean(text)
	var prefix := configured_prefix(settings, "item_barcode_prefix", ".")
	if not prefix.is_empty() and value.begins_with(prefix):
		return value.substr(prefix.length())
	return value

# The class-selection scan field distinguishes borrower cards from item cards.
# An item prefix is required unless the server explicitly configured an empty
# prefix, which means every non-borrower scan is treated as an item.
static func parse_class_scan(text: String, settings: Dictionary) -> Dictionary:
	var value := clean(text)
	if value.is_empty():
		return {"kind": "unknown", "id": ""}

	var borrower_prefix := configured_prefix(settings, "borrower_barcode_prefix", "%")
	if not borrower_prefix.is_empty() and value.begins_with(borrower_prefix):
		return {"kind": "borrower", "id": value.substr(borrower_prefix.length())}

	var item_prefix := configured_prefix(settings, "item_barcode_prefix", ".")
	if item_prefix.is_empty():
		return {"kind": "item", "id": value}
	if value.begins_with(item_prefix):
		return {"kind": "item", "id": value.substr(item_prefix.length())}
	return {"kind": "unknown", "id": ""}
