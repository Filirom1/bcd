class_name ReadingIntro
extends Control

## A story-shelf intro shown while the library is discovered.
## ReadingIntro owns the visuals and animation so SServerDiscovery only handles
## network discovery and asks this component to hide when a server is ready.

const BOOK_START_SCALE := Vector2(0.82, 0.82)
const RUNNER_START_OFFSET := Vector2(-28.0, 14.0)
const RUNNER_TRACK_Y := 374.0
const POPULAR_BOOKS_CACHE = preload("res://src/utils/PopularBooksCache.gd")

@onready var _i18n: Node = get_node("/root/I18n")
@onready var _splash_panel: ColorRect = %SplashPanel
@onready var _splash_title: Label = %SplashTitle
@onready var _splash_shelf: Panel = %StoryShelf
@onready var _splash_runner: Control = %BookmarkRunner
@onready var _portal_glow: Panel = %PortalGlow
@onready var _portal_book: Panel = %PortalBook
@onready var _quote_page: Panel = %QuotePage
@onready var _quote_header: Label = %SplashQuoteHeader
@onready var _message: Label = %SplashMessage
@onready var _author: Label = %SplashAuthor
@onready var _status: Label = %SplashStatus
@onready var _badge: Label = %SplashBadge
@onready var _dots: HBoxContainer = %SplashDots
@onready var _page_turn: ColorRect = %SplashPageTurn
@onready var _world_dragon: Label = %WorldDragon
@onready var _world_space: Label = %WorldSpace
@onready var _world_mystery: Label = %WorldMystery
@onready var _world_laughs: Label = %WorldLaughs
@onready var _world_adventure: Label = %WorldAdventure
@onready var _portal_label: Label = %PortalLabel

var _intro_tween: Tween
var _idle_tween: Tween
var _quote_entries: Array = []
var _quote_entry: Dictionary = {}
var _popular_books: Array[String] = []
var _hidden := false
var _started := false
var _shelf_home := Vector2.ZERO
var _title_home := Vector2.ZERO
var _quote_home := Vector2.ZERO
var _runner_home := Vector2.ZERO
var _portal_home := Vector2.ZERO
var _portal_glow_home := Vector2.ZERO

func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_i18n.locale_changed.connect(_on_locale_changed)
	await get_tree().process_frame
	if _hidden:
		return
	_capture_layout_positions()
	_refresh_text()
	_popular_books = POPULAR_BOOKS_CACHE.load_books()
	_apply_popular_books()
	start_intro()

func _capture_layout_positions() -> void:
	_shelf_home = _splash_shelf.position
	_title_home = _splash_title.position
	_quote_home = _quote_page.position
	_runner_home = _splash_runner.position
	_portal_home = _portal_book.position
	# Derive the highlight from both rectangles instead of duplicating offsets
	# in the scene. This keeps it centered if the portal book is resized.
	_portal_glow_home = _portal_book.position + (_portal_book.size - _portal_glow.size) / 2.0
	_portal_glow.position = _portal_glow_home
	_splash_runner.pivot_offset = _splash_runner.size / 2.0
	_portal_glow.pivot_offset = _portal_glow.size / 2.0
	_portal_book.pivot_offset = _portal_book.size / 2.0
	for book in _story_books():
		book.pivot_offset = book.size / 2.0

func _refresh_text() -> void:
	_splash_title.text = _t("splash.title")
	var version := str(ProjectSettings.get_setting("application/config/version", ""))
	var version_prefix := ("v" + version + " — ") if not version.is_empty() else ""
	_badge.text = version_prefix + _t("splash.open_source")
	_quote_header.text = _t("splash.quote_found")
	_status.text = _t("splash.searching")
	_world_dragon.text = _t("splash.world_dragon")
	_world_space.text = _t("splash.world_space")
	_world_mystery.text = _t("splash.world_mystery")
	_world_laughs.text = _t("splash.world_laughs")
	_world_adventure.text = _t("splash.world_adventure")
	_apply_popular_books()

func _t(key: String) -> String:
	return str(_i18n.call("t", key))

func _apply_popular_books() -> void:
	if _popular_books.is_empty():
		return
	var labels := _world_book_labels()
	var display_titles := _select_display_titles(labels)
	for index in range(display_titles.size()):
		labels[index].text = display_titles[index]

func _world_book_labels() -> Array[Label]:
	return [
		_world_dragon,
		_world_space,
		_world_mystery,
		_world_laughs,
		_world_adventure,
	]

func _select_display_titles(labels: Array[Label]) -> Array[String]:
	var fitting_titles: Array[String] = []
	var long_titles: Array[String] = []
	for title in _popular_books:
		if _title_fits_any(title, labels):
			fitting_titles.append(title)
		else:
			long_titles.append(title)

	# The top 50 are deliberately shuffled only at display time. The cache keeps
	# the complete ranked list, so every launch can show a different selection.
	fitting_titles.shuffle()
	long_titles.shuffle()

	var selected: Array[String] = []
	for label in labels:
		var fitting_index := _first_fitting_title(fitting_titles, label)
		if fitting_index >= 0:
			selected.append(fitting_titles[fitting_index])
			fitting_titles.remove_at(fitting_index)
			continue
		if not long_titles.is_empty():
			selected.append(_truncate_title(long_titles.pop_back(), label))
			continue
		break
	return selected

func _title_fits_any(title: String, labels: Array[Label]) -> bool:
	for label in labels:
		if _title_fits(title, label):
			return true
	return false

func _first_fitting_title(titles: Array[String], label: Label) -> int:
	for index in range(titles.size()):
		if _title_fits(titles[index], label):
			return index
	return -1

func _title_fits(title: String, label: Label) -> bool:
	var font := label.get_theme_font("font")
	var font_size := label.get_theme_font_size("font_size")
	if font == null or label.size.x <= 0.0:
		return title.length() <= 18
	var measured := font.get_multiline_string_size(
		title,
		HORIZONTAL_ALIGNMENT_CENTER,
		label.size.x,
		font_size
	)
	return measured.y <= label.size.y + 1.0

func _truncate_title(title: String, label: Label) -> String:
	var clean := title.strip_edges()
	if _title_fits(clean, label):
		return clean
	var shortened := clean
	while shortened.length() > 1 and not _title_fits(shortened + "…", label):
		shortened = shortened.left(shortened.length() - 1).strip_edges()
	return (shortened + "…") if not shortened.is_empty() else "…"

func _on_locale_changed(_locale: String) -> void:
	_refresh_text()
	_choose_quote()
	if _started and not _hidden:
		_reveal_quote(true)

func start_intro() -> void:
	if not is_inside_tree() or _hidden:
		return
	_started = true
	visible = true
	_splash_panel.modulate = Color.WHITE
	_page_turn.visible = false
	_choose_quote()
	_reset_visual_state()
	_play_intro_sequence()

func _choose_quote() -> void:
	var translations = _i18n.get("translations")
	var locale := str(_i18n.get("current_locale"))
	var locale_data = translations.get(locale, {}) if translations is Dictionary else {}
	var splash_data = locale_data.get("splash", {}) if locale_data is Dictionary else {}
	var configured = splash_data.get("quotes", []) if splash_data is Dictionary else []
	if configured.is_empty() and splash_data is Dictionary:
		configured = splash_data.get("messages", [])
	_quote_entries = configured.duplicate(true) if configured is Array else []
	_quote_entries.shuffle()
	_quote_entry = {}
	if not _quote_entries.is_empty():
		_set_quote_entry(_quote_entries[0])

func _set_quote_entry(entry) -> void:
	if entry is Dictionary:
		_quote_entry = entry.duplicate(true)
		_message.text = str(entry.get("text", ""))
		_author.text = str(entry.get("author", ""))
	else:
		_quote_entry = {"text": str(entry)}
		_message.text = str(entry)
		_author.text = ""
	var long_quote := _message.text.length() > 78
	_message.add_theme_font_size_override("font_size", 18 if long_quote else 21)

func _reset_visual_state() -> void:
	if _intro_tween != null:
		_intro_tween.kill()
	if _idle_tween != null:
		_idle_tween.kill()

	_splash_title.position = _title_home + Vector2(0.0, -18.0)
	_splash_title.modulate.a = 0.0
	_status.modulate.a = 0.0
	_badge.modulate.a = 0.0

	_splash_shelf.position = _shelf_home + Vector2(0.0, 18.0)
	_splash_shelf.modulate.a = 0.0
	for book in _story_books():
		book.scale = BOOK_START_SCALE
		book.modulate.a = 0.0

	_portal_glow.position = _portal_glow_home
	_portal_glow.scale = Vector2(0.72, 0.72)
	_portal_glow.modulate.a = 0.0
	_portal_book.position = _portal_home + Vector2(0.0, 18.0)
	_portal_book.scale = BOOK_START_SCALE
	_portal_book.modulate.a = 0.0

	_splash_runner.position = _runner_home + RUNNER_START_OFFSET
	_splash_runner.modulate.a = 0.0
	_splash_runner.scale = Vector2(0.8, 0.8)

	_quote_page.position = _quote_home + Vector2(48.0, 14.0)
	_quote_page.modulate.a = 0.0
	_quote_header.modulate.a = 0.0
	_message.modulate.a = 0.0
	_author.modulate.a = 0.0
	for dot in _dots.get_children():
		dot.modulate.a = 0.22

func _play_intro_sequence() -> void:
	_intro_tween = create_tween()
	_intro_tween.tween_interval(0.06)
	_intro_tween.tween_property(_splash_title, "position", _title_home, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_intro_tween.parallel().tween_property(_splash_title, "modulate:a", 1.0, 0.24)

	_intro_tween.tween_interval(0.16)
	_intro_tween.tween_property(_splash_shelf, "position", _shelf_home, 0.38).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_intro_tween.parallel().tween_property(_splash_shelf, "modulate:a", 1.0, 0.28)
	for book in _story_books():
		_wake_book(book)

	_intro_tween.tween_interval(0.1)
	_intro_tween.tween_property(_splash_runner, "modulate:a", 1.0, 0.12)
	_intro_tween.parallel().tween_property(_splash_runner, "scale", Vector2.ONE, 0.18).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	for book in _story_books():
		_intro_tween.tween_property(_splash_runner, "position", _runner_target_for(book), 0.34).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		_intro_tween.tween_callback(_pulse_book.bind(book))

	_intro_tween.tween_callback(_activate_portal)
	_intro_tween.tween_interval(0.22)
	_intro_tween.tween_callback(_reveal_quote)
	_intro_tween.tween_property(_status, "modulate:a", 1.0, 0.22)
	_intro_tween.parallel().tween_property(_badge, "modulate:a", 0.58, 0.3)
	_intro_tween.tween_callback(_start_idle_animation)

func _story_books() -> Array[Panel]:
	return [
		%BookDragon,
		%BookSpace,
		%BookMystery,
		%BookLaughs,
		%BookAdventure,
	]

func _wake_book(book: Panel) -> void:
	_intro_tween.tween_property(book, "modulate:a", 1.0, 0.13)
	_intro_tween.parallel().tween_property(book, "scale", Vector2(1.04, 1.04), 0.18).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_intro_tween.tween_property(book, "scale", Vector2.ONE, 0.14).set_trans(Tween.TRANS_SINE)

func _runner_target_for(book: Panel) -> Vector2:
	return Vector2(
		book.position.x + (book.size.x - _splash_runner.size.x) / 2.0,
		RUNNER_TRACK_Y
	)

func _pulse_book(book: Panel) -> void:
	var tw := book.create_tween()
	tw.tween_property(book, "scale", Vector2(1.1, 1.1), 0.12).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(book, "scale", Vector2.ONE, 0.18).set_trans(Tween.TRANS_SINE)

func _activate_portal() -> void:
	var tw := create_tween()
	tw.tween_property(_portal_glow, "modulate:a", 0.9, 0.2)
	tw.parallel().tween_property(_portal_glow, "scale", Vector2(1.12, 1.12), 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(_portal_book, "modulate:a", 1.0, 0.16)
	tw.parallel().tween_property(_portal_book, "position", _portal_home, 0.28).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(_portal_book, "scale", Vector2.ONE, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.tween_property(_portal_glow, "modulate:a", 0.42, 0.35)

func _reveal_quote(immediate := false) -> void:
	if immediate:
		_quote_page.position = _quote_home
		_quote_page.modulate.a = 1.0
		_quote_header.modulate.a = 1.0
		_message.modulate.a = 1.0
		_author.modulate.a = 0.7 if not _author.text.is_empty() else 0.0
		return

	_quote_page.position = _quote_home + Vector2(48.0, 14.0)
	_quote_page.modulate.a = 0.0
	_quote_header.modulate.a = 0.0
	_message.modulate.a = 0.0
	_author.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(_quote_page, "position", _quote_home, 0.44).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tw.parallel().tween_property(_quote_page, "modulate:a", 1.0, 0.24)
	tw.parallel().tween_property(_quote_header, "modulate:a", 1.0, 0.24)
	tw.parallel().tween_property(_message, "modulate:a", 1.0, 0.34)
	if not _author.text.is_empty():
		tw.parallel().tween_property(_author, "modulate:a", 0.7, 0.38)

func _start_idle_animation() -> void:
	if _hidden:
		return
	_idle_tween = create_tween().set_loops()
	_idle_tween.tween_property(_portal_glow, "modulate:a", 0.62, 0.75).set_trans(Tween.TRANS_SINE)
	_idle_tween.parallel().tween_property(_splash_runner, "position:y", RUNNER_TRACK_Y - 4.0, 0.55).set_trans(Tween.TRANS_SINE)
	_idle_tween.tween_property(_portal_glow, "modulate:a", 0.35, 0.75).set_trans(Tween.TRANS_SINE)
	_idle_tween.parallel().tween_property(_splash_runner, "position:y", RUNNER_TRACK_Y, 0.55).set_trans(Tween.TRANS_SINE)

func skip_intro() -> void:
	_hidden = true
	_started = false
	if _intro_tween != null:
		_intro_tween.kill()
	if _idle_tween != null:
		_idle_tween.kill()
	visible = false

func hide_intro() -> void:
	if _hidden:
		return
	_hidden = true
	_started = false
	if _intro_tween != null:
		_intro_tween.kill()
	if _idle_tween != null:
		_idle_tween.kill()

	_page_turn.visible = true
	_page_turn.pivot_offset = Vector2(0.0, _page_turn.size.y / 2.0)
	_page_turn.scale = Vector2(0.02, 1.0)
	_page_turn.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(_page_turn, "scale:x", 1.0, 0.3).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tw.parallel().tween_property(_page_turn, "modulate:a", 0.96, 0.2)
	tw.tween_interval(0.05)
	tw.tween_callback(func():
		visible = false
		_page_turn.visible = false
	)

func cycle_quote_for_test() -> void:
	_choose_quote()
