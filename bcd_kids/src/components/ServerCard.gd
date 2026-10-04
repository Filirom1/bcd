# Server Card Component
class_name ServerCard
extends PanelContainer

const API_HELPERS = preload("res://src/utils/ApiHelpers.gd")

signal connect_pressed(url: String, library_code: String)
signal admin_pressed(web_url: String)

@onready var _name_lbl: Label = %NameLabel
@onready var _host_lbl: Label = %HostLabel
@onready var _admin_btn: Button = %AdminBtn
@onready var _connect_btn: Button = %ConnectBtn

var _peer_url := ""
var _peer_library_code := ""
var _admin_url := ""
var _signals_connected := false

func setup(peer: Dictionary, is_localhost: bool = false) -> void:
	var library_code: String = peer.get("library_code") if peer.get("library_code") is String else I18n.t("server_discovery.default_name")
	var url: String = peer.get("url") if peer.get("url") is String else ""
	var host: String = peer.get("host") if peer.get("host") is String else "localhost"

	_peer_url = url
	_peer_library_code = library_code
	_admin_url = _strip_api_suffix(url)
	_name_lbl.text = "📚 %s" % library_code
	_host_lbl.text = host
	_host_lbl.visible = not host.is_empty()

	_connect_btn.text = I18n.t("server_discovery.connect")
	if not _signals_connected:
		_connect_btn.pressed.connect(func(): connect_pressed.emit(_peer_url, _peer_library_code))

	_admin_btn.text = "🔧 " + I18n.t("auth.admin")
	if not _signals_connected:
		_admin_btn.pressed.connect(func(): admin_pressed.emit(_admin_url))
		_signals_connected = true

	theme_type_variation = "PanelWarning" if is_localhost else "PanelSuccess"

func _strip_api_suffix(url: String) -> String:
	return API_HELPERS.strip_api_suffix(url)
