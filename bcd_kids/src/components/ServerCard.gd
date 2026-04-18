# Server Card Component
class_name ServerCard
extends PanelContainer

signal connect_pressed(url: String, library_code: String)
signal admin_pressed(web_url: String)

@onready var _name_lbl: Label = %NameLabel
@onready var _host_lbl: Label = %HostLabel
@onready var _admin_btn: Button = %AdminBtn
@onready var _connect_btn: Button = %ConnectBtn

func setup(peer: Dictionary, is_localhost: bool = false) -> void:
	var library_code: String = peer.get("library_code") if peer.get("library_code") is String else "BCD"
	var url: String = peer.get("url") if peer.get("url") is String else ""
	var host: String = peer.get("host") if peer.get("host") is String else "localhost"

	_name_lbl.text = "📚 %s" % library_code
	_host_lbl.text = host
	_host_lbl.visible = not host.is_empty()

	_connect_btn.text = I18n.t("server_discovery.connect")
	_connect_btn.pressed.connect(func(): connect_pressed.emit(url, library_code))

	_admin_btn.text = "🔧 Admin"
	var web_url := _strip_api_suffix(url)
	_admin_btn.pressed.connect(func(): admin_pressed.emit(web_url))

	theme_type_variation = "PanelWarning" if is_localhost else "PanelSuccess"

func _strip_api_suffix(url: String) -> String:
	var base := url.rstrip("/")
	if "/api/v1" in base:
		base = base.split("/api/v1")[0]
	return base
