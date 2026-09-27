extends SceneTree

const API_HELPERS = preload("res://src/utils/ApiHelpers.gd")
const GS_SCRIPT = preload("res://autoload/GS.gd")
const I18N_SCRIPT = preload("res://autoload/I18n.gd")

var _assertion_count := 0
var _failures: Array = []

## Headless smoke tests for the Godot client.
##
## Run from the repository root with:
##   python scripts/run_godot_tests.py
##
## The test deliberately exercises dependency-free client helpers. It does not
## start the main scene or make network requests, so it is deterministic and
## safe to run without a BCD server.
func _init() -> void:
	_test_global_state()
	_test_api_helpers()
	_test_i18n_fallbacks()
	_test_server_card_url_normalization()
	# Autoload nodes are created after SceneTree._init(). Defer the small
	# integration check until the project has finished initializing.
	call_deferred("_run_runtime_tests")


func _run_runtime_tests() -> void:
	_test_api_delegation()

	if _failures.is_empty():
		print("Godot tests passed (%d assertions)" % _assertion_count)
		quit(0)
		return

	for failure in _failures:
		push_error("Godot test failed: " + failure)
	print("Godot tests failed (%d/%d assertions)" % [_failures.size(), _assertion_count])
	quit(1)


func _test_global_state() -> void:
	var state = GS_SCRIPT.new()

	_assert(
		state.parse_csv_list(" CP, ,CE1,,  CM2 ") == ["CP", "CE1", "CM2"],
		"GS.parse_csv_list trims values and ignores empty entries"
	)
	_assert(state.parse_csv_list("") == [], "GS.parse_csv_list handles an empty value")

	state.current_borrower = {"id": 17}
	state.current_loans = [{"item_id": "A-1"}]
	state.current_holds = [{"id": 3}]
	state.reserved_biblio_ids = {4: true}
	state.reset_borrower()

	_assert(state.current_borrower.is_empty(), "GS.reset_borrower clears the borrower")
	_assert(state.current_loans.is_empty(), "GS.reset_borrower clears current loans")
	_assert(state.current_holds.is_empty(), "GS.reset_borrower clears current holds")
	_assert(state.reserved_biblio_ids.is_empty(), "GS.reset_borrower clears reservations")


func _test_api_helpers() -> void:
	var api = API_HELPERS

	_assert(
		api.extract_uri("http://127.0.0.1:8888/api/v1/classes") == "/api/v1/classes",
		"API extracts the URI from an absolute URL"
	)
	_assert(
		api.extract_uri("https://library.example") == "/",
		"API uses the root URI when an absolute URL has no path"
	)
	_assert(api.extract_uri("not-a-url") == "/", "API rejects a URL without a scheme")

	var challenge := 'Digest realm="BCD", nonce="nonce-123", qop=auth'
	_assert(
		api.parse_digest_param(challenge, "realm") == "BCD",
		"API parses a quoted digest parameter"
	)
	_assert(
		api.parse_digest_param(challenge, "nonce") == "nonce-123",
		"API parses the digest nonce"
	)
	_assert(
		api.parse_digest_param(challenge, "qop") == "auth",
		"API parses an unquoted digest parameter"
	)
	_assert(
		api.parse_digest_param(challenge, "opaque").is_empty(),
		"API returns an empty value for a missing digest parameter"
	)
	_assert(api.md5("hello") == "5d41402abc4b2a76b9719d911017c592", "API computes MD5")


func _test_api_delegation() -> void:
	var api = get_root().get_node_or_null("API")
	_assert(api != null, "API autoload is available to the test project")
	if api == null:
		return

	_assert(
		api.call("_extract_uri", "http://127.0.0.1:8888/api/v1/classes") == "/api/v1/classes",
		"API transport delegates URI extraction to the helper"
	)
	_assert(
		api.call("_parse_digest_param", 'Digest realm="BCD"', "realm") == "BCD",
		"API transport delegates digest parsing to the helper"
	)
	_assert(
		api.call("_md5", "hello") == "5d41402abc4b2a76b9719d911017c592",
		"API transport delegates MD5 hashing to the helper"
	)

	var card_scene = load("res://src/components/ServerCard.tscn")
	_assert(card_scene != null, "ServerCard scene loads in headless mode")
	if card_scene != null:
		var card = card_scene.instantiate()
		_assert(
			card.call("_strip_api_suffix", "http://localhost:8888/api/v1/")
				== "http://localhost:8888",
			"ServerCard delegates URL normalization to the helper"
		)
		card.free()


func _test_i18n_fallbacks() -> void:
	var i18n = I18N_SCRIPT.new()
	i18n.load_translations()

	_assert(
		i18n.t("this.key.does.not.exist") == "this.key.does.not.exist",
		"I18n falls back to the key for an unknown translation"
	)
	_assert(
		i18n.t("server_discovery.title") != "server_discovery.title",
		"I18n loads the French bundled translation"
	)
	i18n.set_locale("en")
	_assert(
		i18n.t("server_discovery.title") != "server_discovery.title",
		"I18n loads the English bundled translation"
	)


func _test_server_card_url_normalization() -> void:
	var card = API_HELPERS

	_assert(
		card.strip_api_suffix("http://localhost:8888/api/v1/") == "http://localhost:8888",
		"API URL helper removes the API suffix and trailing slash"
	)
	_assert(
		card.strip_api_suffix("https://library.example:9443") == "https://library.example:9443",
		"API URL helper preserves a URL without an API suffix"
	)
	_assert(card.strip_api_suffix("") == "", "API URL helper handles an empty URL")


func _assert(condition: bool, label: String) -> void:
	_assertion_count += 1
	if not condition:
		_failures.append(label)
