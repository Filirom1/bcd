extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
const API_HELPERS = preload("res://src/utils/ApiHelpers.gd")
const BADGE_HELPER = preload("res://src/utils/BadgeHelper.gd")
const GS_SCRIPT = preload("res://autoload/GS.gd")
const I18N_SCRIPT = preload("res://autoload/I18n.gd")
const SETTINGS_SCRIPT = preload("res://autoload/Settings.gd")
const THEME_MANAGER_SCRIPT = preload("res://autoload/ThemeManager.gd")
const CIRCULATION = preload("res://src/utils/CirculationHelper.gd")
const DATA = preload("res://src/utils/DataHelper.gd")

var _test := SUPPORT.new()


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	# Wait for autoload _ready() methods, especially API.HTTPRequest, before
	# exercising methods that intentionally use an empty base URL.
	await _test.wait_frames(self, 3)
	_test_global_state()
	_test_i18n()
	_test_api_helpers()
	_test_api_helpers_on_autoload()
	_test_circulation_helper()
	await _test_badges()
	_test_theme_manager()
	_test_settings()
	await _test_api_wrappers()
	_test.finish(self)


func _test_global_state() -> void:
	var state = GS_SCRIPT.new()
	_test.equal(
		state.parse_csv_list(" CP, ,CE1,,  CM2 "),
		["CP", "CE1", "CM2"],
		"GS.parse_csv_list trims values and ignores empty entries"
	)
	_test.equal(state.parse_csv_list(""), [], "GS.parse_csv_list handles an empty value")
	_test.equal(state.parse_csv_list(" , "), [], "GS.parse_csv_list handles whitespace only")

	state.current_borrower = {"id": 17}
	state.current_loans = [{"item_id": "A-1"}]
	state.current_holds = [{"id": 3}]
	state.set_nav_param("book_data", {"title": "Temporary"})
	state.reset_borrower()

	_test.expect(state.current_borrower.is_empty(), "GS.reset_borrower clears the borrower")
	_test.expect(state.current_loans.is_empty(), "GS.reset_borrower clears current loans")
	_test.expect(state.current_holds.is_empty(), "GS.reset_borrower clears current holds")
	_test.expect(state.nav_params.is_empty(), "GS.reset_borrower clears navigation parameters")


func _test_circulation_helper() -> void:
	_test.equal(
		CIRCULATION.display_title({"display_title": "Display title", "title": "Fallback"}),
		"Display title",
		"Circulation helper prefers the display title"
	)
	_test.equal(
		CIRCULATION.display_title({"title": "Fallback"}),
		"Fallback",
		"Circulation helper falls back to the title"
	)
	_test.equal(
		CIRCULATION.hold_ready_payload({"title": "Book", "hold_ready": {"borrower_name": "Reader", "class_name": "CE1"}}),
		{"title": "Book", "borrower_name": "Reader", "class_name": "CE1", "borrower_id": ""},
		"Circulation helper normalizes ready-hold data"
	)
	_test.equal(CIRCULATION.hold_ready_payload({"title": "Book"}), {}, "Circulation helper ignores returns without a ready hold")
	_test.equal(DATA.text({"publisher": null}, "publisher", "Unknown"), "Unknown", "Data helper handles a null text field")
	_test.equal(DATA.display_value(1.0), "1", "Data helper removes decimal suffix from whole numbers")
	_test.equal(DATA.display_value(1.5), "1.5", "Data helper preserves fractional values")
	_test.equal(DATA.text({"count": 1.0}, "count"), "1", "Data helper formats whole-number API values cleanly")
	_test.equal(DATA.display_title({"display_title": null, "title": "Fallback"}), "Fallback", "Data helper falls back from a null display title")
	_test.equal(DATA.integer({"count": null}, "count", 3), 3, "Data helper handles a null integer field")
	_test.equal(DATA.boolean({"flag": null}, "flag", true), true, "Data helper handles a null boolean field")


func _test_i18n() -> void:
	var i18n = I18N_SCRIPT.new()
	i18n.load_translations()
	_test.expect(i18n.translations.has("fr"), "I18n loads French translations")
	_test.expect(i18n.translations.has("en"), "I18n loads English translations")

	var locale_events: Array = []
	i18n.locale_changed.connect(func(locale): locale_events.append(locale))
	i18n.set_locale("fr")
	_test.expect(i18n.t("server_discovery.title") != "server_discovery.title", "I18n resolves French keys")
	_test.equal(
		i18n.t("search.results_count", {"count": 4}),
		"4 résultats",
		"I18n interpolates French parameters"
	)
	_test.equal(
		i18n.t("main_menu.books_count", {"current": 1.0, "limit": 1.0}),
		"1/1 livres",
		"I18n formats whole-number counters without decimal suffixes"
	)
	i18n.set_locale("en")
	_test.expect(i18n.t("server_discovery.title") != "server_discovery.title", "I18n resolves English keys")
	_test.equal(
		i18n.t("search.results_count", {"count": 4}),
		"4 results",
		"I18n interpolates English parameters"
	)
	var event_count := locale_events.size()
	i18n.set_locale("de")
	_test.equal(i18n.current_locale, "en", "I18n ignores unsupported locales")
	_test.equal(locale_events.size(), event_count, "I18n emits no event for unsupported locales")
	_test.equal(
		i18n.t("this.key.does.not.exist"),
		"this.key.does.not.exist",
		"I18n falls back to the key for an unknown translation"
	)


func _test_api_helpers() -> void:
	_test.equal(
		API_HELPERS.extract_uri("http://127.0.0.1:8888/api/v1/classes"),
		"/api/v1/classes",
		"API extracts the URI from an absolute URL"
	)
	_test.equal(
		API_HELPERS.extract_uri("https://library.example"),
		"/",
		"API uses the root URI when an absolute URL has no path"
	)
	_test.equal(API_HELPERS.extract_uri("not-a-url"), "/", "API rejects a URL without a scheme")
	_test.equal(
		API_HELPERS.extract_uri("http://library.example/?q=hello"),
		"/?q=hello",
		"API preserves the query string in a URI"
	)

	var challenge := 'Digest realm="BCD", nonce="nonce-123", qop=auth'
	_test.equal(
		API_HELPERS.parse_digest_param(challenge, "realm"),
		"BCD",
		"API parses a quoted digest parameter"
	)
	_test.equal(
		API_HELPERS.parse_digest_param(challenge, "nonce"),
		"nonce-123",
		"API parses the digest nonce"
	)
	_test.equal(
		API_HELPERS.parse_digest_param(challenge, "qop"),
		"auth",
		"API parses an unquoted digest parameter"
	)
	_test.equal(
		API_HELPERS.parse_digest_param(challenge, "opaque"),
		"",
		"API returns an empty value for a missing digest parameter"
	)
	_test.equal(API_HELPERS.md5("hello"), "5d41402abc4b2a76b9719d911017c592", "API computes MD5")

	_test.equal(
		API_HELPERS.strip_api_suffix("http://localhost:8888/api/v1/"),
		"http://localhost:8888",
		"API URL helper removes the API suffix and trailing slash"
	)
	_test.equal(
		API_HELPERS.strip_api_suffix("https://library.example:9443"),
		"https://library.example:9443",
		"API URL helper preserves a URL without an API suffix"
	)
	_test.equal(API_HELPERS.strip_api_suffix(""), "", "API URL helper handles an empty URL")


func _test_badges() -> void:
	var gs: Node = get_root().get_node("GS")
	var previous_settings: Dictionary = gs.get("settings")
	gs.set("settings", {
		"catalog_shelf_locations": [
			{"label": "Romans", "color": "#336699"},
			{"label": "Poésie", "color": ""},
		],
		"dewey_colors_enabled": true,
		"dewey_colors": [
			"#111111", "#222222", "#333333", "#444444", "#555555",
			"#666666", "#777777", "#888888", "#999999", "#aaaaaa",
		],
	})

	_test.equal(BADGE_HELPER.auto_text_color(Color("#ffffff")), Color.BLACK, "Badge chooses dark text on light backgrounds")
	_test.equal(BADGE_HELPER.auto_text_color(Color("#000000")), Color.WHITE, "Badge chooses light text on dark backgrounds")
	_test.equal(BADGE_HELPER.get_shelf_color(" Romans "), Color("#336699"), "Badge matches shelf labels after trimming")
	_test.equal(BADGE_HELPER.get_shelf_color("Unknown").a, 0.0, "Badge returns transparent for unknown shelves")
	_test.equal(BADGE_HELPER.get_shelf_color("Poésie").a, 0.0, "Badge returns transparent for an uncoloured shelf")
	_test.equal(BADGE_HELPER.get_dewey_color("843.91 SAI"), Color("#999999"), "Badge maps Dewey first digit to its colour")
	_test.equal(BADGE_HELPER.get_dewey_color(""), Color(0, 0, 0, 0), "Badge ignores an empty call number")
	_test.equal(BADGE_HELPER.get_dewey_color("ABC"), Color(0, 0, 0, 0), "Badge ignores a non-numeric call number")

	var badge_settings: Dictionary = gs.get("settings")
	badge_settings["dewey_colors_enabled"] = false
	_test.equal(BADGE_HELPER.get_dewey_color("843" ).a, 0.0, "Badge honours disabled Dewey colours")
	badge_settings["dewey_colors_enabled"] = true
	badge_settings["dewey_colors"] = ["#ffffff"]
	_test.equal(BADGE_HELPER.get_dewey_color("843").a, 0.0, "Badge ignores an incomplete Dewey palette")

	var shelf_badge = BADGE_HELPER.make_shelf_badge("Romans")
	var cote_badge = BADGE_HELPER.make_cote_badge("843.91 SAI")
	_test.expect(shelf_badge != null, "Badge creates a shelf badge")
	_test.expect(cote_badge != null, "Badge creates a call-number badge")
	_test.equal(BADGE_HELPER.make_shelf_badge(""), null, "Badge omits an empty shelf badge")
	_test.equal(BADGE_HELPER.make_cote_badge(""), null, "Badge omits an empty call-number badge")
	if shelf_badge != null and cote_badge != null:
		var shelf_style := shelf_badge.get_theme_stylebox("panel") as StyleBoxFlat
		var cote_style := cote_badge.get_theme_stylebox("panel") as StyleBoxFlat
		_test.equal(shelf_style.corner_radius_top_left, 4, "Shelf badge uses square corners")
		_test.equal(cote_style.corner_radius_top_left, 20, "Call-number badge uses pill corners")

	var row := HBoxContainer.new()
	BADGE_HELPER.populate_badges(row, "Romans", "843")
	await _test.wait_frames(self)
	_test.equal(row.get_child_count(), 2, "Badge row contains shelf and call-number badges")
	_test.expect(row.visible, "Badge row is visible when it has badges")
	BADGE_HELPER.populate_badges(row, "", "")
	await _test.wait_frames(self)
	_test.equal(row.get_child_count(), 0, "Badge row clears old badges")
	_test.expect(not row.visible, "Badge row hides when it has no badges")
	row.free()
	if shelf_badge != null:
		shelf_badge.free()
	if cote_badge != null:
		cote_badge.free()
	gs.set("settings", previous_settings)


func _test_theme_manager() -> void:
	var manager: Node = get_root().get_node("ThemeManager")
	var previous_name: String = str(manager.get("current_theme_name"))
	var theme_names: Array = THEME_MANAGER_SCRIPT.THEMES.keys()
	_test.expect(theme_names.size() >= 30, "Theme manager exposes the complete theme catalogue")

	for theme_name_variant in theme_names:
		var theme_name := str(theme_name_variant)
		if theme_name == ":random":
			continue
		manager.call("set_theme", theme_name)
		_test.equal(str(manager.get("current_theme_name")), theme_name, "Theme manager activates " + theme_name)
		_test.expect(manager.get("background_texture") != null, "Theme has a background texture: " + theme_name)

	var before_invalid: String = str(manager.get("current_theme_name"))
	manager.call("set_theme", "does-not-exist")
	_test.equal(str(manager.get("current_theme_name")), before_invalid, "Theme manager ignores an unknown theme")
	manager.call("set_theme", ":random")
	_test.expect(str(manager.get("current_theme_name")) != ":random", "Theme manager resolves the random theme key")
	manager.call("set_theme", previous_name)


func _test_settings() -> void:
	var settings: Node = get_root().get_node("Settings")
	var previous_state := {
		"theme": settings.get("theme"),
		"graphics_quality": settings.get("graphics_quality"),
		"resolution": settings.get("resolution"),
		"last_server_url": settings.get("last_server_url"),
		"last_library_name": settings.get("last_library_name"),
		"auth_username": settings.get("auth_username"),
		"auth_password": settings.get("auth_password"),
		"auth_scheme": settings.get("auth_scheme"),
		"auth_server_origin": settings.get("auth_server_origin"),
		"session_auth_username": settings.get("session_auth_username"),
		"session_auth_password": settings.get("session_auth_password"),
		"session_auth_scheme": settings.get("session_auth_scheme"),
		"session_auth_server_origin": settings.get("session_auth_server_origin"),
	}
	settings.call("load_settings")
	settings.call("set_graphics_quality", "low")
	_test.equal(str(settings.call("get_quality_label")), "Basse qualité (vieux PC)", "Settings labels low graphics quality")
	settings.call("set_graphics_quality", "high")
	_test.equal(str(settings.call("get_quality_label")), "Haute qualité (PC récent)", "Settings labels high graphics quality")
	settings.call("set_graphics_quality", "unsupported")
	_test.equal(str(settings.get("graphics_quality")), "low", "Settings normalizes unsupported graphics quality")
	_test.equal(str(settings.call("get_quality_label")), "Basse qualité (vieux PC)", "Settings falls back to low quality")

	settings.call("set_resolution", "720p")
	_test.equal(str(settings.call("get_resolution_label")), "1280×720 (petits écrans)", "Settings labels 720p")
	settings.call("set_resolution", "1080p")
	_test.equal(str(settings.call("get_resolution_label")), "1920×1080 (grands écrans)", "Settings labels 1080p")
	settings.call("set_resolution", "maximized")
	_test.equal(str(settings.call("get_resolution_label")), "Maximisée (recommandé)", "Settings labels maximized mode")
	settings.call("set_resolution", "unsupported")
	_test.equal(str(settings.get("resolution")), "maximized", "Settings normalizes unsupported resolution")
	_test.equal(str(settings.call("get_resolution_label")), "Maximisée (recommandé)", "Settings falls back to maximized mode")

	settings.call("save_server", "http://library.example/api/v1", "School Library")
	_test.equal(str(settings.get("last_server_url")), "http://library.example/api/v1", "Settings stores the last server URL")
	_test.equal(str(settings.get("last_library_name")), "School Library", "Settings stores the library name")
	settings.call("save_auth", "alice", "secret", "digest")
	_test.equal(str(settings.get("auth_username")), "alice", "Settings stores the authentication username")
	_test.equal(str(settings.get("auth_scheme")), "digest", "Settings stores the authentication scheme")
	_test.equal(
		str(settings.get("auth_server_origin")),
		"http://library.example",
		"Settings stores the normalized authentication origin"
	)
	settings.set("auth_server_origin", "")
	_test.expect(settings.call("migrate_legacy_auth"), "Settings migrates legacy credentials using the last server")
	_test.equal(
		str(settings.get("auth_server_origin")),
		"http://library.example",
		"Settings associates migrated credentials with the last server"
	)
	settings.set("auth_server_origin", "")
	settings.call("save_settings")
	settings.call("load_settings")
	_test.equal(
		str(settings.get("auth_server_origin")),
		"http://library.example",
		"Settings migrates legacy credentials while loading the settings file"
	)
	_test.expect(not settings.call("migrate_legacy_auth"), "Settings does not migrate already scoped credentials twice")
	settings.call("clear_auth")
	_test.equal(str(settings.get("auth_username")), "", "Settings clears saved authentication")
	_test.equal(str(settings.get("auth_password")), "", "Settings clears the saved password")

	settings.set("theme", "forest")
	settings.call("save_settings")
	var reloaded = SETTINGS_SCRIPT.new()
	reloaded.load_settings()
	_test.equal(str(reloaded.get("last_server_url")), str(settings.get("last_server_url")), "Settings round-trips the server URL")
	_test.equal(str(reloaded.get("last_library_name")), str(settings.get("last_library_name")), "Settings round-trips the library name")
	_test.equal(str(reloaded.get("theme")), "forest", "Settings round-trips the theme")

	for key in previous_state:
		settings.set(key, previous_state[key])
	settings.call("set_session_auth", {
		"username": previous_state["session_auth_username"],
		"password": previous_state["session_auth_password"],
		"scheme": previous_state["session_auth_scheme"],
		"server_origin": previous_state["session_auth_server_origin"],
	})
	settings.call("save_settings")


func _test_api_helpers_on_autoload() -> void:
	# This function is kept separate so coverage can distinguish helper
	# delegation from the dependency-free helper implementation.
	var api: Node = get_root().get_node("API")
	var settings: Node = get_root().get_node("Settings")
	_test.equal(
		api.call("_extract_uri", "http://127.0.0.1:8888/api/v1/classes"),
		"/api/v1/classes",
		"API transport delegates URI extraction"
	)
	_test.equal(
		api.call("_parse_digest_param", 'Digest realm="BCD"', "realm"),
		"BCD",
		"API transport delegates digest parsing"
	)
	_test.equal(api.call("_md5", "hello"), API_HELPERS.md5("hello"), "API transport delegates MD5 hashing")
	var success_result = api.call("to_result", {"items": []})
	_test.expect(success_result.ok, "API converts a successful legacy response to a typed result")
	_test.equal(success_result.unwrap(), {"items": []}, "Typed API result exposes successful data")
	var error_result = api.call("to_result", {"error": true, "detail": {"code": "network_error", "details": {}}})
	_test.expect(not error_result.ok, "API converts a structured error to a typed result")
	_test.equal(error_result.error_code, "network_error", "Typed API result preserves the error code")
	_test.equal(
		api.call("_find_header", PackedStringArray(["Content-Type: text/plain", "WWW-Authenticate: Digest realm=BCD"]), "www-authenticate"),
		"Digest realm=BCD",
		"API finds headers case-insensitively"
	)
	_test.equal(
		api.call("_find_header", PackedStringArray(["Content-Type: text/plain"]), "missing"),
		"",
		"API returns an empty value for a missing header"
	)

	settings.set("auth_username", "alice")
	settings.set("auth_password", "secret")
	var digest: String = str(api.call(
		"_build_digest_header",
		"GET",
		"/api/v1/classes",
		'Digest realm="BCD", nonce="abc", qop=auth, opaque="opaque-value"'
	))
	_test.expect(str(digest).begins_with("Digest username=\"alice\""), "API builds a digest authorization header")
	_test.expect(str(digest).contains('qop=auth, nc=00000001'), "API includes digest qop fields")
	_test.expect(str(digest).contains('opaque="opaque-value"'), "API preserves the digest opaque value")
	var digest_without_qop: String = str(api.call(
		"_build_digest_header",
		"GET",
		"/",
		'Digest realm="BCD", nonce="abc", algorithm=MD5'
	))
	_test.expect(str(digest_without_qop).contains("response=\""), "API builds a digest response without qop")
	settings.set("auth_username", "")
	settings.set("auth_password", "")


func _test_api_wrappers() -> void:
	var api: Node = get_root().get_node("API")
	var gs: Node = get_root().get_node("GS")
	var previous_base_url: String = str(gs.get("base_url"))
	gs.set("base_url", "")
	await api.call("load_settings")
	_test.equal(await api.call("get_classes"), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API preserves a class-list network error")
	_test.equal(await api.call("get_holds", 7), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API preserves a hold-list network error")
	_test.equal(await api.call("get_students", 7, "Zoé"), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API preserves a borrower search network error")
	_test.equal(await api.call("get_borrower", "card-1"), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API preserves a borrower lookup network error")
	_test.equal(await api.call("get_current_loans", "student-1"), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API preserves a loan lookup network error")
	_test.equal(await api.call("renew_items", "student-1"), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API handles renewals without item IDs")
	_test.equal(await api.call("renew_items", "student-1", ["A-1"]), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API handles renewals with item IDs")
	_test.equal(await api.call("get_bibliographic_record", 4), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API preserves a record lookup network error")
	_test.equal(await api.call("checkout", "student-1", ["A-1"]), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API handles checkout network errors")
	_test.equal(await api.call("return_items", ["A-1"]), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API handles return network errors")
	_test.equal(await api.call("search_catalog", "Harry Potter", {}), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API handles catalog search network errors")
	_test.equal(await api.call("search_catalog", "", {"medium_type": "BD", "target_audience": "CP", "available_only": true}), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API handles all catalog filters")
	_test.equal(await api.call("create_hold", 7, 4), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API handles hold creation network errors")
	_test.equal(await api.call("cancel_hold", 9), {"error": true, "detail": {"code": "network_error", "details": {}}}, "API returns cancellation errors")
	gs.set("base_url", previous_base_url)
