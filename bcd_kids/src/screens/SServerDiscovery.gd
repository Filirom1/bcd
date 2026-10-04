# Screen 0: Server Discovery (mDNS)
extends Control

const SERVER_CARD = preload("res://src/components/ServerCard.tscn")
const MDNS_DISCOVERY = preload("res://src/utils/MdnsDiscovery.gd")
const ERROR_MESSAGES = preload("res://src/utils/ErrorMessages.gd")
const MDNS_TIMEOUT_SECONDS := 2.0
const DEFAULT_SERVER_URL := "http://localhost:8888"
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")
@onready var _title_lbl: Label = %TitleLabel
@onready var _bg: ColorRect = %Background
@onready var _settings_btn: Button = %SettingsBtn
@onready var _fr_btn: Button = %FrBtn
@onready var _en_btn: Button = %EnBtn
@onready var _refresh_btn: Button = %RefreshBtn
@onready var _servers_label: Label = %ServersLabel
@onready var _servers_container: VBoxContainer = %ServersContainer
@onready var _manual_input: LineEdit = %ManualInput
@onready var _connect_manual_btn: Button = %ConnectManualBtn
@onready var _auth_panel: PanelContainer = %AuthPanel
@onready var _auth_title: Label = %AuthTitle
@onready var _use_saved_auth: CheckBox = %UseSavedAuth
@onready var _username_input: LineEdit = %UsernameInput
@onready var _password_input: LineEdit = %PasswordInput
@onready var _auth_scheme_basic: CheckBox = %AuthSchemeBasic
@onready var _auth_scheme_digest: CheckBox = %AuthSchemeDigest
@onready var _retry_btn: Button = %RetryBtn
@onready var _clear_auth_btn: Button = %ClearAuthBtn
@onready var _remember_auth: CheckBox = %RememberAuth

const _LOCAL_CANDIDATES := [
	{"addr": "127.0.0.1", "host": "127.0.0.1"},
	{"addr": "[0:0:0:0:0:0:0:1]", "host": "::1"},
]

var _discovering := false
var _discovery_id := 0
var _last_url := ""
var _last_name := ""
var _connection_attempt_id := 0
var _pending_base_url := ""
var _auth_input_origin := ""
var _suppress_auth_tracking := false

# The intro owns its visuals and animation; discovery only starts and hides it.
@onready var _reading_intro: ReadingIntro = %ReadingIntro

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_manual_input.text = _last_server_base_url()
	_remember_auth.text = I18n.t("auth.remember")
	_remember_auth.button_pressed = false
	_load_saved_auth_for_url(_manual_input.text)
	_username_input.text_changed.connect(_on_auth_input_changed)
	_password_input.text_changed.connect(_on_auth_input_changed)

	_settings_btn.pressed.connect(func(): Mgr.push("settings"))
	_fr_btn.pressed.connect(func():
		I18n.set_locale("fr")
		_refresh_ui()
	)
	_en_btn.pressed.connect(func():
		I18n.set_locale("en")
		_refresh_ui()
	)

	_refresh_ui()
	_refresh_btn.pressed.connect(func(): _discover_servers())

	_connect_manual_btn.pressed.connect(func(): _connect_manual())

	_auth_title.text = "🔐 " + I18n.t("auth.title")

	_username_input.placeholder_text = I18n.t("auth.username_placeholder")
	_password_input.placeholder_text = I18n.t("auth.password_placeholder")

	_auth_scheme_basic.button_pressed = true
	_auth_scheme_digest.button_pressed = false
	_auth_scheme_basic.toggled.connect(func(p): if p: _auth_scheme_digest.button_pressed = false)
	_auth_scheme_digest.toggled.connect(func(p): if p: _auth_scheme_basic.button_pressed = false)

	_use_saved_auth.toggled.connect(_on_use_saved_auth_toggled)

	_retry_btn.pressed.connect(func(): _retry_with_auth())

	_clear_auth_btn.text = I18n.t("auth.clear")
	_clear_auth_btn.pressed.connect(_on_clear_auth)

	_discover_servers()

func _last_server_base_url() -> String:
	var saved_url := Settings.last_server_url.rstrip("/")
	if saved_url.is_empty():
		return _manual_input.text if not _manual_input.text.is_empty() else DEFAULT_SERVER_URL
	if "/api/v1" in saved_url:
		return saved_url.split("/api/v1")[0]
	return saved_url

func _load_saved_auth_for_url(url: String) -> void:
	var saved := Settings.get_saved_auth_for_server(url)
	if saved.is_empty():
		_clear_auth_inputs_only()
		_use_saved_auth.visible = false
		_use_saved_auth.set_pressed_no_signal(false)
		return
	_suppress_auth_tracking = true
	_username_input.text = str(saved.get("username", ""))
	_password_input.text = str(saved.get("password", ""))
	_suppress_auth_tracking = false
	_auth_input_origin = Settings.server_origin(url)
	_auth_scheme_basic.button_pressed = str(saved.get("scheme", "basic")) == "basic"
	_auth_scheme_digest.button_pressed = str(saved.get("scheme", "basic")) == "digest"
	_use_saved_auth.text = I18n.t("auth.use_saved", {"username": saved.get("username", "")})
	_use_saved_auth.button_pressed = true
	_use_saved_auth.visible = true

func _on_auth_input_changed(_value: String) -> void:
	if _suppress_auth_tracking:
		return
	if not _pending_base_url.is_empty():
		_auth_input_origin = Settings.server_origin(_pending_base_url)

func _refresh_ui() -> void:
	_title_lbl.text = I18n.t("server_discovery.title")
	_servers_label.text = I18n.t("server_discovery.servers_available")
	_refresh_btn.text = "🔄 " + I18n.t("server_discovery.refresh")
	_connect_manual_btn.text = I18n.t("server_discovery.connect")
	_retry_btn.text = I18n.t("server_discovery.connect")
	_auth_title.text = "🔐 " + I18n.t("auth.title")
	_remember_auth.text = I18n.t("auth.remember")
	_manual_input.placeholder_text = I18n.t("server_discovery.manual_placeholder")

func _discover_servers() -> void:
	if _discovering:
		return
	_discovery_id += 1
	var discovery_id := _discovery_id
	_discovering = true
	_refresh_btn.disabled = true
	_clear_servers()

	var manual_port := _get_port()
	var proxy_port := _get_client_only_proxy_port(manual_port)

	# CLIENT_ONLY launched by the Python portable runner exposes a tiny
	# loopback mDNS snapshot endpoint. It is optional: standalone Kids falls
	# back to its own PacketPeerUDP DNS-SD client below.
	var mdns_peers: Array = await _fetch_client_only_mdns_peers(proxy_port)
	if discovery_id != _discovery_id or not is_inside_tree():
		return
	if mdns_peers.is_empty():
		var mdns := MDNS_DISCOVERY.new()
		mdns_peers = await mdns.discover(MDNS_TIMEOUT_SECONDS)
		if discovery_id != _discovery_id or not is_inside_tree():
			return

	var working_locals := await _find_working_locals(manual_port, 0.8)
	if discovery_id != _discovery_id or not is_inside_tree():
		return

	# If a local BCD server is available, also use its peer registry. This keeps
	# discovery compatible with existing servers and finds peers missed by the
	# direct multicast query.
	var peers: Array = mdns_peers
	if not working_locals.is_empty():
		var peer_api_url := str(working_locals[0].get("url", "")).rstrip("/") + "/api/v1"
		peers = _merge_peers(peers, await _fetch_peers(peer_api_url))
		if discovery_id != _discovery_id or not is_inside_tree():
			return

	# Probe local ports mentioned by discovered services. This also preserves
	# the localhost fallback when the server and Kids client share a machine.
	var tried_ports := {manual_port: true}
	for peer_variant in peers:
		if not (peer_variant is Dictionary):
			continue
		var peer: Dictionary = peer_variant
		var p := _extract_port(str(peer.get("url", "")))
		if p > 0 and not tried_ports.has(p):
			tried_ports[p] = true
			working_locals += await _find_working_locals(p, 0.8)
			if discovery_id != _discovery_id or not is_inside_tree():
				return

	# Only display peers whose HTTP endpoint responds. Use /health rather than
	# the protected settings endpoint so authentication does not affect probing.
	var shown := 0
	var shown_urls: Dictionary = {}
	for peer_variant in peers:
		if not (peer_variant is Dictionary):
			continue
		var peer: Dictionary = peer_variant
		var peer_api: String = str(peer.get("url", "")).rstrip("/")
		if peer_api.is_empty() or shown_urls.has(peer_api):
			continue
		if await _probe_url(peer_api + "/health", 0.8):
			if discovery_id != _discovery_id or not is_inside_tree():
				return
			_display_servers([peer])
			shown_urls[peer_api] = true
			shown += 1

	# Show local addresses that responded (127.0.0.1 and/or ::1).
	for local_variant in working_locals:
		var local: Dictionary = local_variant
		var local_base_url := str(local.get("url", "")).rstrip("/")
		if local_base_url.is_empty() or shown_urls.has(local_base_url):
			continue
		_add_local_card(local_base_url + "/api/v1", str(local.get("host", "")))
		shown_urls[local_base_url] = true
		shown += 1

	if shown > 0:
		_hide_splash()
		_refresh_btn.disabled = false
		_discovering = false
		return

	# Nothing found yet — retry loop for slow server startup on HDD.
	# Connection-refused is instant so each probe normally costs < 50 ms.
	var deadline := Time.get_ticks_msec() + 8500
	while Time.get_ticks_msec() < deadline:
		working_locals = await _find_working_locals(manual_port, 0.8)
		if discovery_id != _discovery_id or not is_inside_tree():
			return
		if not working_locals.is_empty():
			_hide_splash()
			for local_variant in working_locals:
				var local: Dictionary = local_variant
				_add_local_card(
					str(local.get("url", "")).rstrip("/") + "/api/v1",
					str(local.get("host", ""))
				)
			_refresh_btn.disabled = false
			_discovering = false
			return
		await get_tree().create_timer(0.5).timeout

	_hide_splash()
	_refresh_btn.disabled = false
	_discovering = false

func _get_port() -> int:
	return _extract_port(_manual_input.text.strip_edges())

func _get_client_only_proxy_port(fallback: int) -> int:
	var configured := OS.get_environment("BCD_MDNS_PROXY_PORT").strip_edges()
	if configured.is_valid_int():
		var port := configured.to_int()
		if port > 0 and port <= 65535:
			return port
	return fallback

func _extract_port(text: String, default_port: int = 8888) -> int:
	if text.is_empty():
		return default_port
	if "://" in text:
		text = text.split("://")[1]
	if "/" in text:
		text = text.split("/")[0]
	# rfind handles IPv6 brackets: [::1]:8080
	var last_colon := text.rfind(":")
	if last_colon == -1:
		return default_port
	var port_str := text.substr(last_colon + 1)
	if port_str.is_valid_int():
		var port := port_str.to_int()
		if port > 0 and port <= 65535:
			return port
	return default_port

func _probe_url(url: String, timeout: float) -> bool:
	var http := HTTPRequest.new()
	http.timeout = timeout
	add_child(http)
	var error := http.request(url, [], HTTPClient.METHOD_GET)
	if error != OK:
		http.queue_free()
		return false
	var response = await http.request_completed
	http.queue_free()
	# 401/403 still prove that the endpoint exists and needs credentials;
	# 404/5xx do not count as a working BCD API or proxy.
	return (response[1] >= 200 and response[1] < 300) or response[1] in [401, 403]

func _find_working_locals(port: int, timeout: float) -> Array:
	var result := []
	for candidate in _LOCAL_CANDIDATES:
		var base_url := "http://%s:%d" % [candidate.addr, port]
		if await _probe_url(base_url + "/health", timeout):
			result.append({"url": base_url, "host": candidate.host})
	return result

func _fetch_client_only_mdns_peers(port: int) -> Array:
	if port <= 0:
		return []
	var http := HTTPRequest.new()
	http.timeout = 1.0
	add_child(http)
	var error := http.request(
		"http://127.0.0.1:%d/api/v1/collections/peers" % port,
		[],
		HTTPClient.METHOD_GET
	)
	if error != OK:
		http.queue_free()
		return []
	var response = await http.request_completed
	http.queue_free()
	if response[1] != 200:
		return []
	var json := JSON.new()
	if json.parse(response[3].get_string_from_utf8()) != OK:
		return []
	return json.data if json.data is Array else []

func _fetch_peers(base_url: String = "") -> Array:
	if base_url.is_empty():
		base_url = GS.base_url
	var http := HTTPRequest.new()
	http.timeout = 3.0
	add_child(http)
	var error := http.request(base_url.rstrip("/") + "/collections/peers", [], HTTPClient.METHOD_GET)
	if error != OK:
		http.queue_free()
		return []
	var response = await http.request_completed
	http.queue_free()
	if response[1] != 200:
		return []
	var json := JSON.new()
	if json.parse(response[3].get_string_from_utf8()) != OK:
		return []
	return json.data if json.data is Array else []

func _merge_peers(primary: Array, secondary: Array) -> Array:
	var merged: Array = []
	var by_url: Dictionary = {}
	for source in [primary, secondary]:
		for peer_variant in source:
			if not (peer_variant is Dictionary):
				continue
			var peer: Dictionary = peer_variant
			var url := str(peer.get("url", "")).rstrip("/")
			if url.is_empty():
				continue
			if by_url.has(url):
				var existing: Dictionary = by_url[url]
				if str(existing.get("library_code", "")).is_empty():
					existing["library_code"] = peer.get("library_code", "")
				continue
			var copy: Dictionary = peer.duplicate(true)
			copy["url"] = url
			merged.append(copy)
			by_url[url] = copy
	return merged

func _add_local_card(api_url: String, host_label: String) -> void:
	var card := SERVER_CARD.instantiate() as ServerCard
	_servers_container.add_child(card)
	card.setup({"library_code": I18n.t("server_discovery.localhost_default"), "url": api_url, "host": host_label}, true)
	card.connect_pressed.connect(_select_server)
	card.admin_pressed.connect(func(url): OS.shell_open(url))

func _display_servers(peers: Array) -> void:
	for peer_variant in peers:
		if not (peer_variant is Dictionary):
			continue
		var peer: Dictionary = peer_variant
		var card := SERVER_CARD.instantiate() as ServerCard
		_servers_container.add_child(card)
		card.setup(peer, bool(peer.get("local", false)))
		card.connect_pressed.connect(_select_server)
		card.admin_pressed.connect(func(url): OS.shell_open(url))

func _select_server(url: String, library_code: String) -> void:
	# A connection attempt has its own generation because two selections can be
	# made while the first HTTP request is still pending.
	_connection_attempt_id += 1
	var attempt_id := _connection_attempt_id
	_discovery_id += 1
	_discovering = false
	_refresh_btn.disabled = false
	_last_url = url
	_last_name = library_code

	var base_url := _base_server_url(url)
	var api_url := base_url + "/api/v1"
	_pending_base_url = base_url
	var credentials := _auth_from_ui_for_server(base_url)
	var generation := Mgr.navigation_generation
	# Query the candidate URL without changing the active global server. One
	# settings request is sufficient for both connection validation and loading
	# the candidate server configuration.
	var settings_result = await API.load_settings_for_server(api_url, credentials)
	if not _is_connection_attempt_current(attempt_id, generation):
		return

	if settings_result is Dictionary and settings_result.has("error"):
		var error_code := ERROR_MESSAGES.code(settings_result)
		if error_code == "auth_required":
			_auth_panel.visible = true
			_remember_auth.visible = true
			Mgr.notify(I18n.t("auth.required"), "warning")
			return
		Mgr.notify(ERROR_MESSAGES.message(settings_result, ERROR_MESSAGES.DISCOVERY), "error")
		return

	# Publish the selected server only after all candidate requests have passed.
	GS.base_url = api_url
	GS.library_name = library_code if not library_code.is_empty() else I18n.t("server_discovery.default_name")
	if credentials.is_empty():
		Settings.clear_session_auth()
	else:
		Settings.set_session_auth(credentials)
		if _remember_auth.button_pressed:
			Settings.save_auth(
				str(credentials.get("username", "")),
				str(credentials.get("password", "")),
				str(credentials.get("scheme", "basic")),
				base_url
			)
	Settings.save_server(api_url, GS.library_name)
	API.apply_settings(settings_result)
	# Refresh the single local popular-books list only after the user has
	# connected successfully. The API autoload owns the async work so navigation
	# to the next screen does not cancel the cache update.
	API.refresh_popular_books()
	Mgr.notify(I18n.t("server_discovery.connected", {"name": GS.library_name}), "success")
	await get_tree().create_timer(0.5).timeout
	if not _is_connection_attempt_current(attempt_id, generation):
		return
	Mgr.replace("class_select")

func _base_server_url(url: String) -> String:
	var base_url := url.strip_edges().rstrip("/")
	if "/api/v1" in base_url:
		base_url = base_url.split("/api/v1")[0].rstrip("/")
	return base_url

func _is_connection_attempt_current(attempt_id: int, generation: int) -> bool:
	return is_inside_tree() \
		and attempt_id == _connection_attempt_id \
		and Mgr.is_generation_current(generation)

func _auth_from_ui_for_server(base_url: String) -> Dictionary:
	var origin := Settings.server_origin(base_url)
	if _use_saved_auth.visible and _use_saved_auth.button_pressed:
		var saved := Settings.get_saved_auth_for_server(base_url)
		if not saved.is_empty():
			_auth_input_origin = origin
			return saved
		# Never fall back to fields that may contain credentials for another origin.
		_clear_auth_inputs_only()
		_use_saved_auth.set_pressed_no_signal(false)
	if not _auth_input_origin.is_empty() and _auth_input_origin != origin:
		_clear_auth_inputs_only()
		_use_saved_auth.set_pressed_no_signal(false)
		return {}
	var username := _username_input.text.strip_edges()
	var password := _password_input.text.strip_edges()
	if username.is_empty() or password.is_empty():
		return {}
	_auth_input_origin = origin
	return {
		"username": username,
		"password": password,
		"scheme": "basic" if _auth_scheme_basic.button_pressed else "digest",
		"server_origin": origin,
	}

func _retry_with_auth() -> void:
	if _last_url.is_empty():
		return
	_auth_panel.visible = false
	_select_server(_last_url, _last_name)

func _connect_manual() -> void:
	var url := _manual_input.text.strip_edges()
	if url.is_empty():
		Mgr.notify(I18n.t("server_discovery.enter_url"), "error")
		return
	_select_server(url, url)

func _clear_servers() -> void:
	NODE_HELPER.clear_children(_servers_container)

func _on_use_saved_auth_toggled(pressed: bool) -> void:
	_use_saved_auth.set_pressed_no_signal(pressed)
	if pressed:
		_load_saved_auth_for_url(_pending_base_url if not _pending_base_url.is_empty() else _manual_input.text)
	else:
		# Disabling saved credentials only changes this attempt. The explicit
		# clear action below is the only operation that deletes saved credentials.
		_clear_auth_inputs_only()
		_remember_auth.visible = true

func _clear_auth_inputs_only() -> void:
	_suppress_auth_tracking = true
	_username_input.text = ""
	_password_input.text = ""
	_suppress_auth_tracking = false
	_auth_input_origin = ""
	_auth_scheme_basic.button_pressed = true
	_auth_scheme_digest.button_pressed = false

func _on_clear_auth() -> void:
	Settings.clear_auth()
	_clear_auth_inputs_only()
	_use_saved_auth.set_pressed_no_signal(false)
	_use_saved_auth.visible = false
	_remember_auth.button_pressed = false
	_remember_auth.visible = false
	Mgr.notify(I18n.t("auth.cleared"), "warning")

func _apply_auth_from_ui() -> Dictionary:
	var base_url := _pending_base_url
	if base_url.is_empty():
		base_url = _base_server_url(_manual_input.text)
	var credentials := _auth_from_ui_for_server(base_url)
	if not credentials.is_empty():
		Settings.set_session_auth(credentials)
		if _remember_auth.button_pressed:
			Settings.save_auth(
				str(credentials.get("username", "")),
				str(credentials.get("password", "")),
				str(credentials.get("scheme", "basic")),
				base_url
			)
	return credentials

func _hide_splash() -> void:
	_reading_intro.hide_intro()
