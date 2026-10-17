class_name BookActionFeedback
extends Control

const DATA = preload("res://src/utils/DataHelper.gd")

@onready var _shade: ColorRect = %Shade
@onready var _confetti: CPUParticles2D = %Confetti
@onready var _card: PanelContainer = %Card
@onready var _cover_frame: PanelContainer = %CoverFrame
@onready var _cover_image: CoverImage = %CoverImage
@onready var _cover_placeholder: Label = %CoverPlaceholder
@onready var _book_spine: ColorRect = %BookSpine
@onready var _action_icon: Label = %ActionIcon
@onready var _heading: Label = %Heading
@onready var _book_title: Label = %BookTitle
@onready var _authors: Label = %Authors
@onready var _illustrators: Label = %Illustrators

var _card_style: StyleBoxFlat
var _cover_style: StyleBoxFlat
var _pending_actions: Array[Dictionary] = []
var _sparkles: Array[Label] = []
var _is_playing := false


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_sparkles = [%SparkLeft, %SparkRight, %SparkTop, %SparkBottom]
	resized.connect(_position_confetti)
	_position_confetti()
	_cover_image.cover_loaded.connect(_on_cover_loaded)
	_cover_image.cover_failed.connect(_on_cover_failed)
	_cover_image.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_cover_placeholder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var panel_style := _card.get_theme_stylebox("panel") as StyleBoxFlat
	if panel_style == null:
		push_error("BookActionFeedback requires a StyleBoxFlat on its card.")
		return
	_card_style = panel_style.duplicate() as StyleBoxFlat
	_card.add_theme_stylebox_override("panel", _card_style)
	var cover_panel_style := _cover_frame.get_theme_stylebox("panel") as StyleBoxFlat
	if cover_panel_style == null:
		push_error("BookActionFeedback requires a StyleBoxFlat on its cover frame.")
		return
	_cover_style = cover_panel_style.duplicate() as StyleBoxFlat
	_cover_frame.add_theme_stylebox_override("panel", _cover_style)


func show_action(book: Dictionary, action: String) -> void:
	if action != "checkout" and action != "return":
		push_error("Unknown book action for confirmation: " + action)
		return
	_pending_actions.append({"book": book.duplicate(true), "action": action})
	if not _is_playing:
		_play_next()


func _play_next() -> void:
	if _pending_actions.is_empty():
		visible = false
		_is_playing = false
		return

	_is_playing = true
	var action_data: Dictionary = _pending_actions.pop_front()
	var book: Dictionary = action_data["book"]
	var action: String = action_data["action"]
	var is_checkout := action == "checkout"
	var accent := ThemeManager.ACCENT if is_checkout else ThemeManager.PRIMARY
	var card_color := ThemeManager.BG_WHITE.lerp(accent, 0.06)

	_heading.text = I18n.t("checkout.success") if is_checkout else I18n.t("return.success")
	_book_title.text = DATA.text(book, "title")
	if _book_title.text.is_empty():
		_book_title.text = DATA.display_title(book)
	if _book_title.text.is_empty():
		_book_title.text = I18n.t("common.unknown_title")
	_authors.text = _people_text(book, "authors", "author", "book_detail.authors")
	_illustrators.text = _people_text(book, "illustrators", "illustrator", "book_detail.illustrators")
	_authors.visible = not _authors.text.is_empty()
	_illustrators.visible = not _illustrators.text.is_empty()
	_action_icon.text = "📚" if is_checkout else "↩"
	_action_icon.add_theme_color_override("font_color", accent)
	_card_style.bg_color = card_color
	_card_style.border_color = accent
	var shadow := accent
	shadow.a = 0.36
	_card_style.shadow_color = shadow
	_cover_style.bg_color = ThemeManager.BG_WHITE.lerp(accent, 0.28)
	_heading.add_theme_color_override("font_color", ThemeManager.PRIMARY)
	_book_title.add_theme_color_override("font_color", ThemeManager.TEXT_DARK)
	_authors.add_theme_color_override("font_color", ThemeManager.TEXT)
	_illustrators.add_theme_color_override("font_color", ThemeManager.TEXT)
	_cover_placeholder.add_theme_color_override("font_color", ThemeManager.TEXT_DARK)
	var shade_color := ThemeManager.BG_DARK_OVERLAY
	shade_color.a = 0.22
	_shade.color = shade_color
	_confetti.modulate = accent.lightened(0.25)
	_confetti.restart()
	for index in range(_sparkles.size()):
		var sparkle := _sparkles[index]
		sparkle.add_theme_color_override("font_color", accent.lightened(0.2))
		sparkle.scale = Vector2(0.2, 0.2)
		sparkle.rotation_degrees = -20.0 if index % 2 == 0 else 20.0
		sparkle.modulate.a = 0.0
		var sparkle_tween := create_tween()
		sparkle_tween.set_parallel()
		var delay := float(index) * 0.04
		sparkle_tween.tween_property(sparkle, "scale", Vector2(1.2, 1.2), 0.3).set_delay(delay).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		sparkle_tween.tween_property(sparkle, "modulate:a", 1.0, 0.12).set_delay(delay)
		sparkle_tween.tween_property(sparkle, "modulate:a", 0.0, 0.5).set_delay(delay + 0.25)

	_cover_image.cancel()
	_cover_image.texture = null
	_cover_image.visible = false
	_book_spine.visible = false
	_cover_placeholder.text = "📖\n" + _book_title.text
	_cover_placeholder.visible = true
	var cover_filename := DATA.text(book, "cover_image").strip_edges()
	if not cover_filename.is_empty():
		_cover_image.load_cover(cover_filename)

	visible = true
	_card.pivot_offset = _card.size * 0.5
	_card.scale = Vector2(0.72, 0.72)
	_card.rotation_degrees = -6.0 if is_checkout else 6.0
	_card.modulate.a = 0.0
	var entrance := create_tween()
	entrance.set_parallel()
	entrance.tween_property(_card, "scale", Vector2.ONE, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	entrance.tween_property(_card, "rotation_degrees", 0.0, 0.3)
	entrance.tween_property(_card, "modulate:a", 1.0, 0.18)

	await get_tree().create_timer(0.78).timeout
	if not is_inside_tree():
		return
	var exit_tween := create_tween()
	exit_tween.set_parallel()
	exit_tween.tween_property(_card, "scale", Vector2(1.06, 1.06), 0.2)
	exit_tween.tween_property(_card, "modulate:a", 0.0, 0.2)
	await exit_tween.finished
	if not is_inside_tree():
		return
	_play_next()


func _on_cover_loaded(_texture: Texture2D) -> void:
	_cover_image.visible = true
	_book_spine.color = _card_style.border_color
	_book_spine.visible = true
	_cover_placeholder.visible = false


func _on_cover_failed() -> void:
	_cover_image.visible = false
	_book_spine.visible = false
	_cover_placeholder.visible = true


func _position_confetti() -> void:
	_confetti.position = size * 0.5


func _people_text(book: Dictionary, array_key: String, single_key: String, label_key: String) -> String:
	var names: Array[String] = []
	for person in DATA.array(book, array_key):
		var name := str(person).strip_edges()
		if not name.is_empty():
			names.append(name)
	if names.is_empty():
		var single_name := DATA.text(book, single_key).strip_edges()
		if not single_name.is_empty():
			names.append(single_name)
	if names.is_empty():
		return ""
	return "%s : %s" % [I18n.t(label_key), ", ".join(names)]
