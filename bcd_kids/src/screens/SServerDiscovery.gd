# Screen 0: Server Discovery (mDNS)
extends Control

const SERVER_CARD = preload("res://src/components/ServerCard.tscn")
const MDNS_DISCOVERY = preload("res://src/utils/MdnsDiscovery.gd")
const MDNS_TIMEOUT_SECONDS := 2.0
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

const _LOCAL_CANDIDATES := [
	{"addr": "127.0.0.1", "host": "127.0.0.1"},
	{"addr": "[::1]", "host": "::1"},
]

var _discovering := false
var _last_url := ""
var _last_name := ""

# Splash screen (nodes defined in .tscn)
@onready var _splash: ColorRect = %SplashPanel
@onready var _splash_book: Label = %SplashBook
@onready var _splash_title: Label = %SplashTitle
@onready var _splash_tagline: Label = %SplashTagline
@onready var _splash_msg_lbl: Label = %SplashMessage
@onready var _splash_author_lbl: Label = %SplashAuthor
@onready var _splash_badge: Label = %SplashBadge
@onready var _splash_dots_container: HBoxContainer = %SplashDots

var _splash_dots: Array = []
var _splash_msg_idx := 0
var _splash_cycling := false
var _splash_msgs_shuffled: Array = []

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_manual_input.text = _last_server_base_url()

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
	_username_input.text = Settings.auth_username

	_password_input.placeholder_text = I18n.t("auth.password_placeholder")
	_password_input.text = Settings.auth_password

	_auth_scheme_basic.button_pressed = (Settings.auth_scheme != "digest")
	_auth_scheme_digest.button_pressed = (Settings.auth_scheme == "digest")
	_auth_scheme_basic.toggled.connect(func(p): if p: _auth_scheme_digest.button_pressed = false)
	_auth_scheme_digest.toggled.connect(func(p): if p: _auth_scheme_basic.button_pressed = false)

	if not Settings.auth_username.is_empty():
		_use_saved_auth.text = I18n.t("auth.use_saved", {"username": Settings.auth_username})
		_use_saved_auth.button_pressed = true
		_use_saved_auth.visible = true
		_use_saved_auth.toggled.connect(_on_use_saved_auth_toggled)

	_retry_btn.pressed.connect(func(): _retry_with_auth())

	_clear_auth_btn.text = I18n.t("auth.clear")
	_clear_auth_btn.pressed.connect(_on_clear_auth)

	_init_splash()
	_discover_servers()

func _last_server_base_url() -> String:
	var saved_url := Settings.last_server_url.rstrip("/")
	if saved_url.is_empty():
		return _manual_input.text
	if "/api/v1" in saved_url:
		return saved_url.split("/api/v1")[0]
	return saved_url

func _refresh_ui() -> void:
	_title_lbl.text = I18n.t("server_discovery.title")
	_servers_label.text = I18n.t("server_discovery.servers_available")
	_refresh_btn.text = "🔄 " + I18n.t("server_discovery.refresh")
	_connect_manual_btn.text = I18n.t("server_discovery.connect")
	_retry_btn.text = I18n.t("server_discovery.connect")

func _discover_servers() -> void:
	if _discovering:
		return
	_discovering = true
	_refresh_btn.disabled = true
	_clear_servers()

	var manual_port := _get_port()
	var proxy_port := _get_client_only_proxy_port(manual_port)

	# CLIENT_ONLY launched by the Python portable runner exposes a tiny
	# loopback mDNS snapshot endpoint. It is optional: standalone Kids falls
	# back to its own PacketPeerUDP DNS-SD client below.
	var mdns_peers: Array = await _fetch_client_only_mdns_peers(proxy_port)
	if mdns_peers.is_empty():
		var mdns := MDNS_DISCOVERY.new()
		mdns_peers = await mdns.discover(MDNS_TIMEOUT_SECONDS)

	var working_locals := await _find_working_locals(manual_port, 0.8)

	# If a local BCD server is available, also use its peer registry. This keeps
	# discovery compatible with existing servers and finds peers missed by the
	# direct multicast query.
	var peers: Array = mdns_peers
	if not working_locals.is_empty():
		var previous_base_url := GS.base_url
		GS.base_url = working_locals[0].url + "/api/v1"
		peers = _merge_peers(peers, await _fetch_peers())
		GS.base_url = previous_base_url if previous_base_url else ""

	# Probe local ports mentioned by discovered services. This also preserves
	# the localhost fallback when the server and Kids client share a machine.
	var tried_ports := {manual_port: true}
	for peer in peers:
		var p := _extract_port(peer.get("url", ""))
		if p > 0 and not tried_ports.has(p):
			tried_ports[p] = true
			working_locals += await _find_working_locals(p, 0.8)

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
		if await _probe_url(base_url + "/api/v1/admin/settings", timeout):
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

func _fetch_peers() -> Array:
	var http := HTTPRequest.new()
	http.timeout = 3.0
	add_child(http)
	var error := http.request(GS.base_url + "/collections/peers", [], HTTPClient.METHOD_GET)
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
	for peer in peers:
		var card := SERVER_CARD.instantiate() as ServerCard
		_servers_container.add_child(card)
		card.setup(peer as Dictionary, peer.get("local", false))
		card.connect_pressed.connect(_select_server)
		card.admin_pressed.connect(func(url): OS.shell_open(url))

func _select_server(url: String, library_code: String) -> void:
	_last_url = url
	_last_name = library_code
	_apply_auth_from_ui()

	var base_url := url.rstrip("/")
	if "/api/v1" in base_url:
		base_url = base_url.split("/api/v1")[0]

	GS.base_url = base_url + "/api/v1"
	GS.library_name = library_code if library_code else "BCD"

	var result = await API.get_settings()

	if result is Dictionary and result.has("error"):
		var error_code: String = result.get("detail", {}).get("code", "unknown_error")
		if error_code == "auth_required":
			_auth_panel.visible = true
			Mgr.notify(I18n.t("auth.required"), "warning")
			return
		Mgr.notify(I18n.t("server_discovery.connection_error"), "error")
		GS.base_url = ""
		GS.library_name = ""
	else:
		Settings.save_server(base_url + "/api/v1", library_code)
		await API.load_settings()
		Mgr.notify(I18n.t("server_discovery.connected", {"name": library_code}), "success")
		await get_tree().create_timer(0.5).timeout
		Mgr.replace("class_select")

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
	for c in _servers_container.get_children():
		c.queue_free()

func _on_use_saved_auth_toggled(pressed: bool) -> void:
	if pressed:
		_username_input.text = Settings.auth_username
		_password_input.text = Settings.auth_password
		_auth_scheme_basic.button_pressed = Settings.auth_scheme == "basic"
		_auth_scheme_digest.button_pressed = Settings.auth_scheme == "digest"
	else:
		_username_input.text = ""
		_password_input.text = ""

func _on_clear_auth() -> void:
	Settings.clear_auth()
	_username_input.text = ""
	_password_input.text = ""
	if _use_saved_auth.visible:
		_use_saved_auth.button_pressed = false
	Mgr.notify(I18n.t("auth.cleared"), "warning")

func _apply_auth_from_ui() -> void:
	var username := _username_input.text.strip_edges()
	var password := _password_input.text.strip_edges()
	var scheme := "basic" if _auth_scheme_basic.button_pressed else "digest"
	if not username.is_empty() and not password.is_empty():
		Settings.save_auth(username, password, scheme)

func _init_splash() -> void:
	_splash.color = ThemeManager.BG
	_splash_title.text = I18n.t("splash.title")
	_splash_title.add_theme_color_override("font_color", ThemeManager.PRIMARY)
	_splash_title.add_theme_font_size_override("font_size", 80)
	_splash_book.add_theme_color_override("font_color", ThemeManager.SUCCESS)
	_splash_book.add_theme_font_size_override("font_size", 90)
	_splash_tagline.text = I18n.t("splash.tagline")
	_splash_tagline.add_theme_font_size_override("font_size", 13)
	_splash_tagline.modulate.a = 0.4
	var _version: String = ProjectSettings.get_setting("application/config/version", "")
	var _version_prefix: String = ("v" + _version + " — ") if not _version.is_empty() else ""
	_splash_badge.text = _version_prefix + I18n.t("splash.open_source")
	_splash_badge.add_theme_font_size_override("font_size", 11)
	_splash_dots = []
	for dot in _splash_dots_container.get_children():
		dot.add_theme_color_override("font_color", ThemeManager.PRIMARY)
		_splash_dots.append(dot)
	# Wait one frame so nodes have computed sizes (needed for pivot_offset)
	await get_tree().process_frame
	_splash_book.pivot_offset = _splash_book.size / 2.0
	_splash_title.pivot_offset = _splash_title.size / 2.0
	for dot in _splash_dots:
		(dot as Label).pivot_offset = (dot as Label).size / 2.0
	_spawn_floating_stars()
	_animate_splash_book()
	_animate_splash_title()
	_animate_splash_dots()
	_splash_cycling = true
	_shuffle_and_start()

func _animate_splash_book() -> void:
	_splash_book.scale = Vector2(0.2, 0.2)
	var tw_in := _splash_book.create_tween()
	tw_in.tween_property(_splash_book, "scale", Vector2(1.25, 1.25), 0.5).set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
	tw_in.tween_property(_splash_book, "scale", Vector2(1.0, 1.0), 0.2).set_trans(Tween.TRANS_SINE)
	tw_in.tween_callback(func():
		var tw := _splash_book.create_tween().set_loops()
		# Squish down like landing
		tw.tween_property(_splash_book, "scale", Vector2(1.15, 0.82), 0.45).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
		# Stretch up like bouncing
		tw.tween_property(_splash_book, "scale", Vector2(0.9, 1.18), 0.2).set_trans(Tween.TRANS_SINE)
		# Settle
		tw.tween_property(_splash_book, "scale", Vector2(1.0, 1.0), 0.25).set_trans(Tween.TRANS_BOUNCE).set_ease(Tween.EASE_OUT)
		tw.tween_interval(0.9)
	)

func _animate_splash_title() -> void:
	# Pop in from nothing with overshoot
	_splash_title.scale = Vector2(0.05, 0.05)
	_splash_title.modulate.a = 0.0
	var tw := _splash_title.create_tween()
	tw.tween_interval(0.45)
	tw.tween_property(_splash_title, "scale", Vector2(1.3, 1.3), 0.4).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(_splash_title, "modulate:a", 1.0, 0.2)
	tw.tween_property(_splash_title, "scale", Vector2(1.0, 1.0), 0.18).set_trans(Tween.TRANS_SINE)
	tw.tween_callback(func():
		# Subtle scale pulse loop
		var tw2 := _splash_title.create_tween().set_loops()
		tw2.tween_property(_splash_title, "scale", Vector2(1.06, 1.06), 1.6).set_trans(Tween.TRANS_SINE)
		tw2.tween_property(_splash_title, "scale", Vector2(1.0, 1.0), 1.6).set_trans(Tween.TRANS_SINE)
	)

func _animate_splash_dots() -> void:
	for i in range(_splash_dots.size()):
		var dot: Label = _splash_dots[i]
		var tw := dot.create_tween().set_loops()
		tw.tween_interval(i * 0.2)
		# Squish flat
		tw.tween_property(dot, "scale", Vector2(1.5, 0.5), 0.1).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
		# Pop up tall
		tw.tween_property(dot, "scale", Vector2(0.7, 1.55), 0.15).set_trans(Tween.TRANS_SINE)
		# Bounce settle
		tw.tween_property(dot, "scale", Vector2(1.0, 1.0), 0.25).set_trans(Tween.TRANS_BOUNCE).set_ease(Tween.EASE_OUT)
		tw.tween_interval(0.5 + (2 - i) * 0.12)

func _spawn_floating_stars() -> void:
	var icons := ["\u2728", "\u2b50", "\u2605", "\u2728", "\u2b50", "\u2605"]
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	var w := _splash.size.x
	var h := _splash.size.y
	for icon in icons:
		var star := Label.new()
		star.text = icon
		star.add_theme_font_size_override("font_size", rng.randi_range(18, 40))
		var sx := rng.randf_range(0.05, 0.92) * w
		var sy := rng.randf_range(0.15, 0.88) * h
		star.position = Vector2(sx, sy)
		star.z_index = -1
		var start_a: float = rng.randf_range(0.25, 0.65)
		star.modulate.a = start_a
		_splash.add_child(star)
		var dist := rng.randf_range(55.0, 115.0)
		var dur := rng.randf_range(2.5, 5.0)
		var tw := star.create_tween().set_loops()
		tw.tween_interval(rng.randf_range(0.0, 2.5))
		tw.tween_property(star, "position:y", sy - dist, dur).set_trans(Tween.TRANS_SINE)
		tw.parallel().tween_property(star, "modulate:a", 0.0, dur * 0.65).set_trans(Tween.TRANS_SINE)
		tw.tween_callback(func():
			star.position.y = sy
			star.modulate.a = start_a
		)

func _shuffle_and_start() -> void:
	var msgs: Array = I18n.translations.get(I18n.current_locale, {}).get("splash", {}).get("messages", [])
	_splash_msgs_shuffled = msgs.duplicate()
	_splash_msgs_shuffled.shuffle()
	_splash_msg_idx = 0
	_cycle_splash_messages()

func _cycle_splash_messages() -> void:
	if not _splash_cycling or not is_instance_valid(_splash_msg_lbl):
		return
	if _splash_msgs_shuffled.is_empty():
		return
	if _splash_msg_idx >= _splash_msgs_shuffled.size():
		_splash_msgs_shuffled.shuffle()
		_splash_msg_idx = 0
	var entry = _splash_msgs_shuffled[_splash_msg_idx]
	_splash_msg_idx += 1

	var msg_text: String
	var author_text: String = ""
	var is_citation := false
	if entry is Dictionary:
		msg_text = entry.get("text", "")
		author_text = entry.get("author", "")
		is_citation = entry.get("type", "punchline") == "citation"
	else:
		msg_text = str(entry)

	if is_citation:
		_splash_msg_lbl.add_theme_font_size_override("font_size", 20)
		_splash_msg_lbl.add_theme_color_override("font_color", ThemeManager.SUCCESS)
	else:
		_splash_msg_lbl.add_theme_font_size_override("font_size", 34)
		_splash_msg_lbl.add_theme_color_override("font_color", ThemeManager.WARNING)

	_splash_msg_lbl.text = msg_text
	_splash_author_lbl.text = author_text
	_splash_author_lbl.modulate.a = 0.0

	# Punch in: scale-down from big + fade in (video game style)
	_splash_msg_lbl.modulate.a = 0.0
	_splash_msg_lbl.scale = Vector2(1.5, 1.5)
	var tw := _splash_msg_lbl.create_tween()
	tw.tween_property(_splash_msg_lbl, "scale", Vector2(1.0, 1.0), 0.28).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(_splash_msg_lbl, "modulate:a", 1.0, 0.2)
	if not author_text.is_empty():
		tw.parallel().tween_property(_splash_author_lbl, "modulate:a", 0.6, 0.4)
	tw.tween_interval(2.1)
	tw.tween_property(_splash_msg_lbl, "modulate:a", 0.0, 0.28).set_trans(Tween.TRANS_SINE)
	tw.parallel().tween_property(_splash_author_lbl, "modulate:a", 0.0, 0.28)
	tw.tween_callback(_cycle_splash_messages)

func _hide_splash() -> void:
	_splash_cycling = false
	# Game-style exit: scale up slightly + fade
	_splash.pivot_offset = _splash.size / 2.0
	var tw := create_tween()
	tw.tween_property(_splash, "scale", Vector2(1.08, 1.08), 0.3).set_trans(Tween.TRANS_SINE)
	tw.parallel().tween_property(_splash, "modulate:a", 0.0, 0.35).set_trans(Tween.TRANS_SINE)
	tw.tween_callback(func(): _splash.visible = false)
