# Autoload "Settings" - User Settings Management
extends Node

const SETTINGS_FILE = "user://bcd_settings.cfg"

# Config cache to avoid repeated disk reads (HDD optimization)
var _config_cache: ConfigFile = null

# Active theme name (must be a key in ThemeManager.THEMES)
var theme := "forest"

# Graphics quality: "low" (vieux PC) or "high" (PC puissants)
var graphics_quality := "low"

# Resolution presets: "720p", "1080p", "maximized"
var resolution := "maximized"

# Last used server and credentials (for auto-reconnect)
var last_server_url := ""
var last_library_name := ""
var auth_username := ""
var auth_password := ""
var auth_scheme := "basic"  # "basic" or "digest"

# Available resolution presets
const RESOLUTIONS = {
	"720p": Vector2i(1280, 720),
	"1080p": Vector2i(1920, 1080),
	"maximized": Vector2i(0, 0)  # Special value for maximized window
}

func _ready() -> void:
	load_settings()
	ThemeManager.set_theme(theme)
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

	var err = config.save(SETTINGS_FILE)
	if err == OK:
		print("[Settings] Settings saved: quality=%s, resolution=%s, server=%s" % [graphics_quality, resolution, last_library_name])
	else:
		print("[Settings] Failed to save settings: %d" % err)

func set_theme(name: String) -> void:
	theme = name
	save_settings()
	ThemeManager.set_theme(name)

func set_graphics_quality(quality: String) -> void:
	graphics_quality = quality
	save_settings()
	apply_graphics_quality()

func set_resolution(res: String) -> void:
	resolution = res
	save_settings()
	apply_resolution()

func apply_graphics_quality() -> void:
	var viewport = get_tree().root
	if not viewport:
		print("[Settings] No viewport found, deferring graphics settings")
		return

	match graphics_quality:
		"low":
			# Vieux PC: texture pixelisée, pas d'antialiasing
			viewport.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
			viewport.msaa_2d = Viewport.MSAA_DISABLED
			print("[Settings] Applied LOW quality (nearest neighbor, no AA)")
		"high":
			# PC puissant: texture lissée, antialiasing
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
		"low": return "Basse (vieux PC)"
		"high": return "Haute (PC récent)"
		_: return "Inconnu"

func get_resolution_label() -> String:
	match resolution:
		"720p": return "1280×720 (petits écrans)"
		"1080p": return "1920×1080 (grands écrans)"
		"maximized": return "Fenêtre maximisée"
		_: return "Inconnu"

func save_server(url: String, library_name: String) -> void:
	last_server_url = url
	last_library_name = library_name
	save_settings()

func save_auth(username: String, password: String, scheme: String = "basic") -> void:
	auth_username = username
	auth_password = password
	auth_scheme = scheme
	save_settings()

func clear_auth() -> void:
	auth_username = ""
	auth_password = ""
	save_settings()
