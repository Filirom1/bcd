extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")

var _test := SUPPORT.new()
var _screen: Control
var _settings: Node
var _i18n: Node
var _previous_auth_username := ""
var _previous_auth_password := ""
var _previous_auth_scheme := ""
var _previous_auth_origin := ""
var _previous_session_username := ""
var _previous_session_password := ""
var _previous_session_scheme := ""
var _previous_session_origin := ""


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	await _test.wait_frames(self, 3)
	_settings = get_root().get_node("Settings")
	_i18n = get_root().get_node("I18n")
	_previous_auth_username = str(_settings.get("auth_username"))
	_previous_auth_password = str(_settings.get("auth_password"))
	_previous_auth_scheme = str(_settings.get("auth_scheme"))
	_previous_auth_origin = str(_settings.get("auth_server_origin"))
	_previous_session_username = str(_settings.get("session_auth_username"))
	_previous_session_password = str(_settings.get("session_auth_password"))
	_previous_session_scheme = str(_settings.get("session_auth_scheme"))
	_previous_session_origin = str(_settings.get("session_auth_server_origin"))
	await _mount_discovery_screen()
	_test_scene_initialization()
	_test_url_helpers()
	await _test_network_fallbacks()
	await _test_server_cards()
	await _test_auth_controls()
	await _test_splash_states()
	await _unmount_discovery_screen()
	await _test_intro_skipped_on_server_switch()
	_settings.auth_username = _previous_auth_username
	_settings.auth_password = _previous_auth_password
	_settings.auth_scheme = _previous_auth_scheme
	_settings.auth_server_origin = _previous_auth_origin
	_settings.call("set_session_auth", {
		"username": _previous_session_username,
		"password": _previous_session_password,
		"scheme": _previous_session_scheme,
		"server_origin": _previous_session_origin,
	})
	_settings.call("save_settings")
	_test.finish(self)


func _mount_discovery_screen() -> void:
	_screen = load("res://src/screens/SServerDiscovery.tscn").instantiate()
	# _ready() normally starts network discovery. Mark the screen busy before it
	# enters the tree so this test can exercise the real UI initialization without
	# waiting for multicast or a school server.
	_screen.set("_discovering", true)
	get_root().add_child(_screen)
	await _test.wait_frames(self, 3)
	_test.expect(_screen.is_inside_tree(), "Server discovery screen enters the tree")


func _test_scene_initialization() -> void:
	_test.expect(
		not _screen.get_node("MainMargin/Root/TitleLabel").text.is_empty(),
		"Server discovery initializes its translated title"
	)
	_test.expect(
		not _screen.get_node("MainMargin/Root/ServersLabel").text.is_empty(),
		"Server discovery initializes its server-list label"
	)
	var settings: Node = get_root().get_node("Settings")
	var saved_url := str(settings.get("last_server_url")).rstrip("/")
	var expected_address := saved_url.split("/api/v1")[0] if "/api/v1" in saved_url else saved_url
	if expected_address.is_empty():
		expected_address = "http://localhost:8888"
	_test.equal(
		_screen.get_node("MainMargin/Root/ManualRow/ManualInput").text,
		expected_address,
		"Server discovery starts with the saved address or localhost fallback"
	)
	_screen.call("_refresh_ui")
	_screen.call("_discover_servers")
	_test.expect(_screen.get("_discovering"), "Server discovery ignores a refresh while a scan is already running")


func _test_url_helpers() -> void:
	var settings: Node = get_root().get_node("Settings")
	var previous_url := str(settings.get("last_server_url"))
	var manual_input: LineEdit = _screen.get_node("MainMargin/Root/ManualRow/ManualInput")

	settings.set("last_server_url", "http://library.example:9443/api/v1/")
	_test.equal(
		str(_screen.call("_last_server_base_url")),
		"http://library.example:9443",
		"Server discovery removes the API suffix from a saved URL"
	)
	settings.set("last_server_url", "")
	manual_input.text = "typed-address"
	_test.equal(
		str(_screen.call("_last_server_base_url")),
		"typed-address",
		"Server discovery keeps the manually typed address when no URL is saved"
	)
	settings.set("last_server_url", previous_url)

	manual_input.text = "http://library.example:9010/api/v1"
	_test.equal(_screen.call("_get_port"), 9010, "Server discovery extracts the manual port")
	_test.equal(_screen.call("_get_client_only_proxy_port", 9010), 9010, "Server discovery falls back to the manual port for its proxy")
	_test.equal(_screen.call("_extract_port", ""), 8888, "Server discovery uses the default port for an empty address")
	_test.equal(_screen.call("_extract_port", "https://library.example"), 8888, "Server discovery uses the default port when none is supplied")
	_test.equal(_screen.call("_extract_port", "http://library.example:65535/path"), 65535, "Server discovery accepts the largest TCP port")
	_test.equal(_screen.call("_extract_port", "http://library.example:0"), 8888, "Server discovery rejects port zero")
	_test.equal(_screen.call("_extract_port", "http://library.example:65536"), 8888, "Server discovery rejects an out-of-range port")
	_test.equal(_screen.call("_extract_port", "http://library.example:not-a-port"), 8888, "Server discovery rejects a non-numeric port")
	_test.equal(_screen.call("_extract_port", "[::1]:9001"), 9001, "Server discovery extracts a port from a bracketed IPv6 address")


func _test_network_fallbacks() -> void:
	_test.equal(await _screen.call("_fetch_client_only_mdns_peers", 0), [], "Server discovery skips an invalid proxy port")
	var gs: Node = get_root().get_node("GS")
	var previous_peer_base := str(gs.get("base_url"))
	gs.set("base_url", "http://127.0.0.1:65534/api/v1")
	_test.equal(await _screen.call("_fetch_peers"), [], "Server discovery handles an unavailable peer endpoint")
	gs.set("base_url", previous_peer_base)
	_test.equal(
		await _screen.call("_probe_url", "http://127.0.0.1:65534/health", 0.01),
		false,
		"Server discovery rejects an unreachable health endpoint"
	)
	_test.equal(
		await _screen.call("_find_working_locals", 65534, 0.01),
		[],
		"Server discovery does not report unreachable loopback candidates"
	)

	var settings: Node = get_root().get_node("Settings")
	var previous_last_url := str(settings.get("last_server_url"))
	var previous_base := str(get_root().get_node("GS").get("base_url"))
	var previous_name := str(get_root().get_node("GS").get("library_name"))
	get_root().get_node("GS").set("base_url", "")
	await _screen.call("_select_server", "http://127.0.0.1:65534/api/v1", "Unavailable")
	_test.equal(get_root().get_node("GS").get("base_url"), "", "Server discovery clears the base URL after a connection error")
	_test.equal(get_root().get_node("GS").get("library_name"), "", "Server discovery clears the library name after a connection error")
	get_root().get_node("GS").set("base_url", previous_base)
	get_root().get_node("GS").set("library_name", previous_name)
	_screen.set("_last_url", "")
	_screen.call("_retry_with_auth")
	_test.expect(not _screen.get_node("MainMargin/Root/AuthPanel").visible, "Server discovery ignores an auth retry before a server is selected")

	settings.set("last_server_url", "")
	_screen.get_node("MainMargin/Root/ManualRow/ManualInput").text = ""
	_screen.call("_connect_manual")
	var manager: Node = get_root().get_node("Mgr")
	var notifications: VBoxContainer = manager.get("_notif_box")
	var last_message := ""
	if notifications != null and notifications.get_child_count() > 0:
		var notification: Node = notifications.get_child(notifications.get_child_count() - 1)
		last_message = notification.get_node("MessageLabel").text
	_test.equal(
		last_message,
		_i18n.call("t", "server_discovery.enter_url"),
		"Server discovery reports an empty manual address"
	)
	settings.set("last_server_url", previous_last_url)



func _test_server_cards() -> void:
	var servers: VBoxContainer = _screen.get_node("MainMargin/Root/ServersScroll/ServersContainer")
	_screen.call("_clear_servers")
	await _test.wait_frames(self)
	_screen.call("_add_local_card", "http://127.0.0.1:8888/api/v1", "127.0.0.1")
	await _test.wait_frames(self)
	_test.equal(servers.get_child_count(), 1, "Server discovery creates a localhost server card")
	_test.equal(
		servers.get_child(0).get_node("Row/Info/HostLabel").text,
		"127.0.0.1",
		"Server discovery passes the local host label to the card"
	)

	_screen.call("_display_servers", [{
		"url": "http://annex.example:9000",
		"library_code": "Annex",
		"host": "annex.example",
	}])
	await _test.wait_frames(self)
	_test.equal(servers.get_child_count(), 2, "Server discovery displays a discovered peer card")
	_test.equal(
		servers.get_child(1).get_node("Row/Info/NameLabel").text,
		"📚 Annex",
		"Server discovery passes the peer library name to the card"
	)
	_screen.call("_clear_servers")
	await _test.wait_frames(self)
	_test.equal(servers.get_child_count(), 0, "Server discovery clears old server cards")


func _test_auth_controls() -> void:
	var settings: Node = get_root().get_node("Settings")
	var previous_username := str(settings.get("auth_username"))
	var previous_password := str(settings.get("auth_password"))
	var previous_scheme := str(settings.get("auth_scheme"))
	var username: LineEdit = _screen.get_node("MainMargin/Root/AuthPanel/AuthContent/CredsRow/UsernameInput")
	var password: LineEdit = _screen.get_node("MainMargin/Root/AuthPanel/AuthContent/CredsRow/PasswordInput")
	var basic: CheckBox = _screen.get_node("MainMargin/Root/AuthPanel/AuthContent/AuthBottom/AuthSchemeBasic")
	var digest: CheckBox = _screen.get_node("MainMargin/Root/AuthPanel/AuthContent/AuthBottom/AuthSchemeDigest")

	settings.set("auth_username", "saved-user")
	settings.set("auth_password", "saved-secret")
	settings.set("auth_scheme", "digest")
	_screen.get_node("MainMargin/Root/ManualRow/ManualInput").text = "http://localhost:8888"
	_screen.set("_pending_base_url", "")
	settings.set("auth_server_origin", settings.call("server_origin", "http://localhost:8888"))
	_screen.call("_on_use_saved_auth_toggled", true)
	_test.equal(username.text, "saved-user", "Server discovery restores a saved username")
	_test.equal(password.text, "saved-secret", "Server discovery restores a saved password")
	_test.expect(digest.button_pressed and not basic.button_pressed, "Server discovery restores the saved auth scheme")
	_screen.call("_on_use_saved_auth_toggled", false)
	_test.equal(username.text, "", "Server discovery clears the username when saved auth is disabled")
	_test.equal(password.text, "", "Server discovery clears the password when saved auth is disabled")
	_test.equal(settings.get("auth_username"), "saved-user", "Disabling saved auth keeps the saved username")
	_test.equal(settings.get("auth_password"), "saved-secret", "Disabling saved auth keeps the saved password")

	_screen.set("_pending_base_url", "http://127.0.0.1:8888")
	username.text = "teacher"
	password.text = "secret"
	var origin_a: Dictionary = _screen.call("_auth_from_ui_for_server", "http://127.0.0.1:8888")
	var origin_b: Dictionary = _screen.call("_auth_from_ui_for_server", "http://localhost:8888")
	_test.equal(origin_a.get("username", ""), "teacher", "Server discovery accepts credentials for their selected origin")
	_test.equal(origin_b, {}, "Server discovery does not reuse credentials for another origin")

	username.text = "teacher"
	password.text = "secret"
	basic.button_pressed = true
	digest.button_pressed = false
	_screen.get_node("MainMargin/Root/AuthPanel/AuthContent/RememberAuth").button_pressed = true
	_screen.call("_apply_auth_from_ui")
	_test.equal(settings.get("auth_username"), "teacher", "Server discovery saves credentials only when requested")
	_test.equal(settings.get("auth_scheme"), "basic", "Server discovery saves the selected basic auth scheme")

	_screen.call("_on_clear_auth")
	_test.equal(settings.get("auth_username"), "", "Server discovery clears the saved username")
	_test.equal(settings.get("auth_password"), "", "Server discovery clears the saved password")

	settings.set("auth_username", previous_username)
	settings.set("auth_password", previous_password)
	settings.set("auth_scheme", previous_scheme)
	settings.call("save_settings")


func _test_splash_states() -> void:
	var intro: Control = _screen.get_node("ReadingIntro")
	var message: Label = intro.get_node("SplashPanel/SplashCenter/SplashCanvas/SplashMessage")
	var author: Label = intro.get_node("SplashPanel/SplashCenter/SplashCanvas/SplashAuthor")
	_test.expect(intro is ReadingIntro, "Server discovery owns a dedicated reading intro component")
	_test.expect(not message.text.is_empty(), "Reading intro selects a localized quote")

	intro.call("_set_quote_entry", {"type": "citation", "text": "A quote", "author": "An author"})
	_test.equal(message.text, "A quote", "Reading intro displays a quote")
	_test.equal(author.text, "An author", "Reading intro displays an optional quote author")
	intro.call("_set_quote_entry", "A page adventure")
	_test.equal(message.text, "A page adventure", "Reading intro handles a plain quote entry")

	_test.expect(is_instance_valid(_screen), "Server discovery remains mounted during the reading intro")
	_screen.call("_hide_splash")
	await create_timer(0.45).timeout
	_test.expect(not intro.visible, "Server discovery hides the dedicated reading intro")


func _test_intro_skipped_on_server_switch() -> void:
	get_root().get_node("GS").call("set_nav_param", "skip_reading_intro", true)
	await _mount_discovery_screen()
	var intro: Control = _screen.get_node("ReadingIntro")
	_test.expect(not intro.visible, "Returning to server selection skips the reading intro")
	_test.expect(bool(intro.get("_hidden")), "Skipped reading intro stays hidden after initialization")
	await _unmount_discovery_screen()


func _unmount_discovery_screen() -> void:
	if is_instance_valid(_screen):
		_screen.queue_free()
	await _test.wait_frames(self, 3)
