# Autoload "Mgr" - Screen Manager + Notifications
extends CanvasLayer

const NOTIFICATION = preload("res://src/components/Notification.tscn")

var _stack: Array = []
var _notif_box: VBoxContainer
var _screen_cache: Dictionary = {}
var _bg_tex_rect: TextureRect

func _ready() -> void:
	layer = 0
	_build_background()
	_build_notif_layer()
	call_deferred("push", "server_discovery")

# ============================================================================
# Background Image (behind all screens)
# ============================================================================

func _build_background() -> void:
	var bg_layer := CanvasLayer.new()
	bg_layer.layer = -10
	add_child(bg_layer)

	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bg_layer.add_child(root)

	_bg_tex_rect = TextureRect.new()
	_bg_tex_rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_bg_tex_rect.texture = ThemeManager.background_texture
	_bg_tex_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	_bg_tex_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_bg_tex_rect)

	ThemeManager.theme_changed.connect(_on_theme_changed)

func _on_theme_changed() -> void:
	_bg_tex_rect.texture = ThemeManager.background_texture
	var new_theme := get_tree().root.theme
	for scr in _screen_cache.values():
		scr.theme = new_theme
		var bg = scr.get_node_or_null("%Background")
		if bg is ColorRect:
			bg.color = ThemeManager.BG
	for scr in _stack:
		if scr not in _screen_cache.values():
			scr.theme = new_theme
			var bg = scr.get_node_or_null("%Background")
			if bg is ColorRect:
				bg.color = ThemeManager.BG

# ============================================================================
# Notification Layer (always on top)
# ============================================================================

func _build_notif_layer() -> void:
	var nl := CanvasLayer.new()
	nl.layer = 20
	add_child(nl)

	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	nl.add_child(root)

	_notif_box = VBoxContainer.new()
	_notif_box.anchor_left = 0.0
	_notif_box.anchor_right = 1.0
	_notif_box.anchor_top = 1.0
	_notif_box.anchor_bottom = 1.0
	_notif_box.offset_top = -180
	_notif_box.offset_bottom = 0.0
	_notif_box.alignment = BoxContainer.ALIGNMENT_END
	_notif_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_notif_box.add_theme_constant_override("separation", 4)
	root.add_child(_notif_box)

# ============================================================================
# Splash Screen (Initial Loading)
# ============================================================================

# ============================================================================
# Navigation (Screen Stack)
# ============================================================================

func push(name: String) -> void:
	if not _stack.is_empty():
		_hide_screen(_stack.back() as Control)
	var scr := _make(name)
	_stack.append(scr)
	if not scr.is_inside_tree():
		add_child(scr)
	_show_screen(scr)

func pop() -> void:
	if _stack.size() <= 1:
		return
	var old_screen := _stack.pop_back() as Control
	var is_cached := old_screen in _screen_cache.values()
	if not is_cached:
		old_screen.queue_free()
	else:
		_hide_screen(old_screen)
	_show_screen(_stack.back() as Control)

func replace(name: String) -> void:
	if not _stack.is_empty():
		var old_screen := _stack.pop_back() as Control
		var is_cached := old_screen in _screen_cache.values()
		if not is_cached:
			old_screen.queue_free()
		else:
			_hide_screen(old_screen)
	push(name)

func _hide_screen(scr: Control) -> void:
	scr.hide()
	scr.process_mode = Node.PROCESS_MODE_DISABLED

func _show_screen(scr: Control) -> void:
	scr.process_mode = Node.PROCESS_MODE_INHERIT
	scr.show()

func _make(name: String) -> Control:
	if _screen_cache.has(name):
		print("[Mgr] Using cached screen: %s" % name)
		return _screen_cache[name]

	var scr: Control
	match name:
		"server_discovery": scr = preload("res://src/screens/SServerDiscovery.tscn").instantiate()
		"class_select":     scr = preload("res://src/screens/SClassSelect.tscn").instantiate()
		"name_input":       scr = preload("res://src/screens/SNameInput.tscn").instantiate()
		"name_choice":      scr = preload("res://src/screens/SNameChoice.tscn").instantiate()
		"main_menu":        scr = preload("res://src/screens/SMainMenu.tscn").instantiate()
		"checkout":         scr = preload("res://src/screens/SCheckout.tscn").instantiate()
		"return_scan":      scr = preload("res://src/screens/SReturnScan.tscn").instantiate()
		"search":           scr = preload("res://src/screens/SSearch.tscn").instantiate()
		"hold_confirm":     scr = preload("res://src/screens/SHoldConfirm.tscn").instantiate()
		"hold_ready":       scr = preload("res://src/screens/SHoldReady.tscn").instantiate()
		"return_shelve":    scr = preload("res://src/screens/SReturnShelve.tscn").instantiate()
		"book_detail":  	scr = preload("res://src/screens/SBookDetail.tscn").instantiate()
		"my_holds":         scr = preload("res://src/screens/SMyHolds.tscn").instantiate()
		"settings":         scr = preload("res://src/screens/SSettings.tscn").instantiate()
		_:
			push_error("Unknown screen: " + name)
			scr = Control.new()

	scr.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	# FIX: CanvasLayer bloque l'héritage du thème, on l'applique explicitement
	scr.theme = get_tree().root.theme

	if name in ["server_discovery", "class_select", "checkout", "search"]:
		_screen_cache[name] = scr
		print("[Mgr] Cached screen: %s" % name)

	return scr

# ============================================================================
# Notifications (Toast Messages)
# ============================================================================

func notify(text: String, type: String = "success") -> void:
	var notif := NOTIFICATION.instantiate() as Notification
	_notif_box.add_child(notif)
	notif.setup(text, type)

	var tw := notif.create_tween()
	tw.tween_interval(2.4)
	tw.tween_property(notif, "modulate:a", 0.0, 0.45)
	tw.tween_callback(notif.queue_free)
