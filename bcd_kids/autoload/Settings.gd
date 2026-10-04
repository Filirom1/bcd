# Autoload "Settings" - User Settings Management
extends Node

const SETTINGS_FILE = "user://bcd_settings.cfg"

# Config cache to avoid repeated disk reads (HDD optimization)
var _config_cache: ConfigFile = null

# Active theme name (must be a key in ThemeManager.THEMES)
var theme := "forest"

# Graphics quality: "low" for older PCs or "high" for newer PCs.
var graphics_quality := "low"

# Resolution presets: "720p", "1080p", "maximized"
var resolution := "maximized"

# Last used server and credentials (for auto-reconnect)
var last_server_url := ""
var last_library_name := ""
var auth_username := ""
var auth_password := ""
var auth_scheme := "basic"  # "basic" or "digest"
var auth_server_origin := ""

# Session credentials are never written to disk. They are scoped to the
# confirmed server origin and are used for the current application session.
var session_auth_username := ""
var session_auth_password := ""
var session_auth_scheme := "basic"
var session_auth_server_origin := ""

# Available resolution presets
const RESOLUTIONS = {
	"720p": Vector2i(1280, 720),
	"1080p": Vector2i(1920, 1080),
	"maximized": Vector2i(0, 0)  # Special value for maximized window
}

func _ready() -> void:
	load_settings()
	var theme_manager := _theme_manager()
	if theme_manager != null:
		theme_manager.call("set_theme", theme)
	# Wait for scene tree to be ready before applying settings
	await get_tree().process_frame
	await get_tree().process_frame
	apply_resolution()
	apply_graphics_quality()

func load_settings() -> void:
	var config = ConfigFile.new()
	var err = config.load(SETTINGS_FILE)

	# Cache config for future use (HDD optimization)
	if err == OK:
		_config_cache = config

	if err == OK:
		graphics_quality = config.get_value("graphics", "quality", "low")
		resolution = config.get_value("display", "resolution", "maximized")
		theme = config.get_value("display", "theme", "forest")
		last_server_url = config.get_value("server", "url", "")
		last_library_name = config.get_value("server", "library_name", "")
		auth_username = config.get_value("auth", "username", "")
		auth_password = config.get_value("auth", "password", "")
		auth_scheme = config.get_value("auth", "scheme", "basic")
		auth_server_origin = config.get_value("auth", "server_origin", "")
		migrate_legacy_auth()
		print("[Settings] Loaded settings: quality=%s, resolution=%s, server=%s" % [graphics_quality, resolution, last_library_name])
	else:
		print("[Settings] No settings file found, using defaults")

func save_settings() -> void:
	# Reuse cached config if available (HDD optimization)
	var config = _config_cache if _config_cache else ConfigFile.new()
	config.set_value("graphics", "quality", graphics_quality)
	config.set_value("display", "resolution", resolution)
	config.set_value("display", "theme", theme)
	config.set_value("server", "url", last_server_url)
	config.set_value("server", "library_name", last_library_name)
	config.set_value("auth", "username", auth_username)
	config.set_value("auth", "password", auth_password)
	config.set_value("auth", "scheme", auth_scheme)
	config.set_value("auth", "server_origin", auth_server_origin)

	var err = config.save(SETTINGS_FILE)
	if err == OK:
		print("[Settings] Settings saved: quality=%s, resolution=%s, server=%s" % [graphics_quality, resolution, last_library_name])
	else:
		print("[Settings] Failed to save settings: %d" % err)

func set_theme(name: String) -> void:
	theme = name
	save_settings()
	var theme_manager := _theme_manager()
	if theme_manager != null:
		theme_manager.call("set_theme", name)

func set_graphics_quality(quality: String) -> void:
	graphics_quality = quality if quality in ["low", "high"] else "low"
	apply_graphics_quality()
	save_settings()

func set_resolution(res: String) -> void:
	resolution = res if RESOLUTIONS.has(res) else "maximized"
	apply_resolution()
	save_settings()

func apply_graphics_quality() -> void:
	var viewport = get_tree().root
	if not viewport:
		print("[Settings] No viewport found, deferring graphics settings")
		return

	match graphics_quality:
		"low":
			# Older PCs: nearest-neighbour textures and no antialiasing.
			viewport.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
			viewport.msaa_2d = Viewport.MSAA_DISABLED
			print("[Settings] Applied LOW quality (nearest neighbor, no AA)")
		"high":
			# Newer PCs: filtered textures and antialiasing.
			viewport.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_LINEAR_WITH_MIPMAPS
			viewport.msaa_2d = Viewport.MSAA_2X
			print("[Settings] Applied HIGH quality (linear+mipmaps, MSAA 2x)")
		_:
			print("[Settings] Unknown quality: %s, defaulting to low" % graphics_quality)
			graphics_quality = "low"
			apply_graphics_quality()

func apply_resolution() -> void:
	var window = get_tree().root
	if not window:
		print("[Settings] No window found, deferring resolution settings")
		return

	if not RESOLUTIONS.has(resolution):
		print("[Settings] Unknown resolution: %s, defaulting to maximized" % resolution)
		resolution = "maximized"

	if resolution == "maximized":
		# Maximized mode
		window.mode = Window.MODE_MAXIMIZED
		print("[Settings] Applied MAXIMIZED mode")
	else:
		# Fixed resolution
		var size = RESOLUTIONS[resolution]
		window.mode = Window.MODE_WINDOWED
		window.size = size
		# Center window on screen
		var screen_size = DisplayServer.screen_get_size()
		var window_pos = (screen_size - size) / 2
		window.position = window_pos
		print("[Settings] Applied resolution: %s (%dx%d)" % [resolution, size.x, size.y])

func get_quality_label() -> String:
	match graphics_quality:
		"low": return _t("settings.quality_low").replace("\n", " ")
		"high": return _t("settings.quality_high").replace("\n", " ")
		_: return _t("common.error_unknown")

func get_resolution_label() -> String:
	match resolution:
		"720p": return _t("settings.resolution_720p").replace("\n", " ")
		"1080p": return _t("settings.resolution_1080p").replace("\n", " ")
		"maximized": return _t("settings.resolution_maximized").replace("\n", " ")
		_: return _t("common.error_unknown")

func _t(key: String) -> String:
	var main_loop := Engine.get_main_loop()
	if main_loop is SceneTree:
		var i18n := (main_loop as SceneTree).get_root().get_node_or_null("I18n")
		if i18n != null:
			return i18n.call("t", key)
	return key

func save_server(url: String, library_name: String) -> void:
	last_server_url = url
	last_library_name = library_name
	save_settings()

func save_auth(username: String, password: String, scheme: String = "basic", server_url: String = "") -> void:
	auth_username = username
	auth_password = password
	auth_scheme = scheme
	auth_server_origin = server_origin(server_url if not server_url.is_empty() else last_server_url)
	set_session_auth({
		"username": username,
		"password": password,
		"scheme": scheme,
		"server_origin": auth_server_origin,
	})
	save_settings()

func migrate_legacy_auth() -> bool:
	# Older settings files did not record the server origin. The last selected
	# server is the safest available association and preserves the old behavior
	# for installations that normally use one library server.
	if auth_username.is_empty() or auth_password.is_empty() or not auth_server_origin.is_empty():
		return false
	var inferred_origin := server_origin(last_server_url)
	if inferred_origin.is_empty() or not (inferred_origin.begins_with("http://") or inferred_origin.begins_with("https://")):
		return false
	auth_server_origin = inferred_origin
	save_settings()
	return true


func get_saved_auth_for_server(server_url: String) -> Dictionary:
	var origin := server_origin(server_url)
	if origin.is_empty() or origin != auth_server_origin:
		return {}
	if auth_username.is_empty() or auth_password.is_empty():
		return {}
	return {
		"username": auth_username,
		"password": auth_password,
		"scheme": auth_scheme,
		"server_origin": origin,
	}

func set_session_auth(credentials: Dictionary) -> void:
	session_auth_username = str(credentials.get("username", ""))
	session_auth_password = str(credentials.get("password", ""))
	session_auth_scheme = str(credentials.get("scheme", "basic"))
	session_auth_server_origin = str(credentials.get("server_origin", ""))

func get_session_auth_for_server(server_url: String) -> Dictionary:
	var origin := server_origin(server_url)
	if origin.is_empty() or origin != session_auth_server_origin:
		return {}
	if session_auth_username.is_empty() or session_auth_password.is_empty():
		return {}
	return {
		"username": session_auth_username,
		"password": session_auth_password,
		"scheme": session_auth_scheme,
		"server_origin": origin,
	}

func clear_session_auth() -> void:
	session_auth_username = ""
	session_auth_password = ""
	session_auth_scheme = "basic"
	session_auth_server_origin = ""

func clear_auth() -> void:
	auth_username = ""
	auth_password = ""
	auth_scheme = "basic"
	auth_server_origin = ""
	clear_session_auth()
	save_settings()

func server_origin(url: String) -> String:
	var value := url.strip_edges().rstrip("/")
	if value.is_empty():
		return ""
	if "/api/v1" in value:
		value = value.split("/api/v1")[0].rstrip("/")
	var scheme_separator := value.find("://")
	if scheme_separator == -1:
		return value.to_lower()
	var authority_start := scheme_separator + 3
	var slash := value.find("/", authority_start)
	var authority := value.substr(authority_start) if slash == -1 else value.substr(authority_start, slash - authority_start)
	return value.substr(0, authority_start).to_lower() + authority.to_lower()


func _theme_manager() -> Node:
	var tree := get_tree()
	return tree.root.get_node_or_null("ThemeManager") if tree != null else null
