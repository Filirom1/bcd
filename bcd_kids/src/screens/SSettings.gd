# Screen: Settings
extends Control

@onready var _bg: ColorRect = %Background
@onready var _back_btn: Button = %BackBtn
@onready var _current_res_lbl: Label = %CurrentResolutionLabel
@onready var _current_quality_lbl: Label = %CurrentQualityLabel
@onready var _btn_720p: Button = %Btn720p
@onready var _btn_1080p: Button = %Btn1080p
@onready var _btn_max: Button = %BtnMax
@onready var _btn_low: Button = %BtnLowQuality
@onready var _btn_high: Button = %BtnHighQuality
@onready var _theme_prev_btn: Button = %ThemePrevBtn
@onready var _theme_next_btn: Button = %ThemeNextBtn
@onready var _theme_name_lbl: Label = %ThemeNameLabel
@onready var _theme_index_lbl: Label = %ThemeIndexLabel
@onready var _theme_apply_btn: Button = %ThemeApplyBtn
@onready var _theme_preview: TextureRect = %ThemePreview

var _theme_keys: Array = []
var _carousel_index: int = 0
var _original_theme: String = ""

func _ready() -> void:
	_bg.color = ThemeManager.BG
	_original_theme = ThemeManager.current_theme_name
	_current_res_lbl.text = "Resolution actuelle: " + Settings.get_resolution_label()
	_current_quality_lbl.text = "Qualite actuelle: " + Settings.get_quality_label()

	_setup_carousel()

	_back_btn.pressed.connect(_on_back)
	_back_btn.call_deferred("grab_focus")
	_theme_prev_btn.pressed.connect(_on_carousel_prev)
	_theme_next_btn.pressed.connect(_on_carousel_next)
	_theme_apply_btn.pressed.connect(_on_carousel_apply)

	_btn_720p.pressed.connect(func():
		Settings.set_resolution("720p")
		_current_res_lbl.text = "Résolution actuelle: " + Settings.get_resolution_label()
		Mgr.notify("Résolution 720p appliquée", "success")
	)
	_btn_1080p.pressed.connect(func():
		Settings.set_resolution("1080p")
		_current_res_lbl.text = "Résolution actuelle: " + Settings.get_resolution_label()
		Mgr.notify("Résolution 1080p appliquée", "success")
	)
	_btn_max.pressed.connect(func():
		Settings.set_resolution("maximized")
		_current_res_lbl.text = "Résolution actuelle: " + Settings.get_resolution_label()
		Mgr.notify("Fenêtre maximisée", "success")
	)
	_btn_low.pressed.connect(func():
		Settings.set_graphics_quality("low")
		_current_quality_lbl.text = "Qualité actuelle: " + Settings.get_quality_label()
		Mgr.notify("Qualité basse activée", "success")
	)
	_btn_high.pressed.connect(func():
		Settings.set_graphics_quality("high")
		_current_quality_lbl.text = "Qualité actuelle: " + Settings.get_quality_label()
		Mgr.notify("Qualité haute activée", "success")
	)

# ============================================================================
# Theme carousel
# ============================================================================

func _setup_carousel() -> void:
	_theme_keys = ThemeManager.THEMES.keys()
	_carousel_index = _theme_keys.find(ThemeManager.current_theme_name)
	if _carousel_index < 0:
		_carousel_index = 0
	_update_carousel_label()

func _update_carousel_label() -> void:
	var name: String = _theme_keys[_carousel_index]
	var cfg: Dictionary = ThemeManager.THEMES[name]
	var label_key := "label_" + I18n.current_locale
	_theme_name_lbl.text = cfg.get(label_key, name)
	if name == ":random":
		_theme_index_lbl.text = I18n.t("settings.theme_random_hint")
		_theme_preview.texture = null
	else:
		_theme_index_lbl.text = "%d / %d" % [_carousel_index + 1, _theme_keys.size()]
		var bg_path: String = cfg.get("background", "")
		_theme_preview.texture = load(bg_path) if bg_path != "" else null

func _on_carousel_prev() -> void:
	_carousel_index = (_carousel_index - 1 + _theme_keys.size()) % _theme_keys.size()
	_apply_preview()

func _on_carousel_next() -> void:
	_carousel_index = (_carousel_index + 1) % _theme_keys.size()
	_apply_preview()

func _apply_preview() -> void:
	var name: String = _theme_keys[_carousel_index]
	_update_carousel_label()
	if name != ":random":
		ThemeManager.set_theme(name)

func _on_carousel_apply() -> void:
	Settings.set_theme(_theme_keys[_carousel_index])
	_original_theme = ThemeManager.current_theme_name
	var label_key := "label_" + I18n.current_locale
	var label: String = ThemeManager.THEMES[ThemeManager.current_theme_name].get(label_key, ThemeManager.current_theme_name)
	Mgr.notify(I18n.t("settings.theme_applied", {"name": label}), "success")

func _on_back() -> void:
	if ThemeManager.current_theme_name != _original_theme:
		ThemeManager.set_theme(_original_theme)
	Mgr.pop()

func _unhandled_key_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"):
		_on_back()
		get_viewport().set_input_as_handled()
