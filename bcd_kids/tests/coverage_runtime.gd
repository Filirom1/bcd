# Runtime collector used by scripts/run_godot_tests.py --coverage.
#
# This is intentionally a tiny function-level collector. Stock Godot exposes
# no source-line coverage API, and this project does not depend on a patched
# editor or a third-party test addon. The test runner instruments function
# entry points in a temporary project copy and this autoload records hits.
extends Node

var _output_path := ""
var _hits: Dictionary = {}


func _ready() -> void:
	_output_path = OS.get_environment("GODOT_COVERAGE_FILE")


func hit(script_path: String, function_name: String, declaration_line: int) -> void:
	if _output_path.is_empty():
		return
	var script_hits: Dictionary = _hits.get(script_path, {})
	var function_hits: Dictionary = script_hits.get(function_name, {
		"line": declaration_line,
		"hits": 0,
	})
	function_hits["line"] = declaration_line
	function_hits["hits"] = int(function_hits.get("hits", 0)) + 1
	script_hits[function_name] = function_hits
	_hits[script_path] = script_hits


func _exit_tree() -> void:
	_write_report()


func _write_report() -> void:
	if _output_path.is_empty():
		return
	var file := FileAccess.open(_output_path, FileAccess.WRITE)
	if file == null:
		push_error("Unable to write Godot coverage report: " + _output_path)
		return
	file.store_string(JSON.stringify({"hits": _hits}))
	file.close()
