# Autoload "Mgr" - Screen Manager + Notifications
extends CanvasLayer

const NOTIFICATION = preload("res://src/components/Notification.tscn")
const MANAGER_BACKGROUND = preload("res://src/components/ManagerBackground.tscn")
const MANAGER_NOTIFICATIONS = preload("res://src/components/ManagerNotifications.tscn")
const NODE_HELPER = preload("res://src/utils/NodeHelper.gd")

var _stack: Array = []
var _notif_box: VBoxContainer
var _bg_tex_rect: TextureRect

# Incremented whenever navigation starts. Screens use it to ignore results from
# requests that began before the current screen/session became active.
var navigation_generation := 0

func _ready() -> void:
	layer = 0
	_build_background()
	_build_notif_layer()

	# The normal application starts at server discovery. Headless tests create
	# the scenes they need explicitly, so avoid starting network discovery in
	# every test process.
	if not OS.has_environment("BCD_GODOT_TESTS"):
		call_deferred("push", "server_discovery")

# ============================================================================
# Background Image (behind all screens)
# ============================================================================

func _build_background() -> void:
	var background := MANAGER_BACKGROUND.instantiate()
	add_child(background)
	_bg_tex_rect = background.get_node("Root/BackgroundTexture") as TextureRect
	_bg_tex_rect.texture = ThemeManager.background_texture
	ThemeManager.theme_changed.connect(_on_theme_changed)

func _on_theme_changed() -> void:
	_bg_tex_rect.texture = ThemeManager.background_texture
	var new_theme := get_tree().root.theme
	for scr_variant in _stack:
		if not (scr_variant is Control) or not is_instance_valid(scr_variant):
			continue
		var scr: Control = scr_variant
		scr.theme = new_theme
		var bg = scr.get_node_or_null("%Background")
		if bg is ColorRect:
			bg.color = ThemeManager.BG

# ============================================================================
# Notification Layer (always on top)
# ============================================================================

func _build_notif_layer() -> void:
	var notification_layer := MANAGER_NOTIFICATIONS.instantiate()
	add_child(notification_layer)
	_notif_box = notification_layer.get_node("Root/NotificationBox") as VBoxContainer

# ============================================================================
# Navigation (Screen Stack)
# ============================================================================

func push(name: String) -> void:
	# A screen type may occur only once in the stack. Breadcrumbs and repeated
	# button presses should reveal the existing screen rather than add a second
	# instance of it.
	if _find_stack_index(name) >= 0:
		pop_to(name)
		return

	navigation_generation += 1
	if not _stack.is_empty():
		_hide_screen(_stack.back() as Control)
	_push_new(name)

func pop() -> void:
	if _stack.size() <= 1:
		return

	navigation_generation += 1
	var old_screen := _stack.pop_back() as Control
	_dispose(old_screen)
	_show_screen(_stack.back() as Control)

func replace(name: String) -> void:
	if _stack.is_empty():
		push(name)
		return

	navigation_generation += 1
	var old_screen := _stack.pop_back() as Control
	_dispose(old_screen)

	var existing := _find_stack_index(name)
	if existing >= 0:
		while _stack.size() - 1 > existing:
			_dispose(_stack.pop_back() as Control)
		_show_screen(_stack.back() as Control)
		return

	_push_new(name)

func reset_to(name: String) -> void:
	# Used for logout/server changes. No old screen, cached data, or pending
	# screen instance may remain reachable from the navigation stack.
	navigation_generation += 1
	while not _stack.is_empty():
		_dispose(_stack.pop_back() as Control)
	_push_new(name)

func pop_to(name: String) -> void:
	var target := _find_stack_index(name)
	if target < 0:
		replace(name)
		return

	navigation_generation += 1
	while _stack.size() - 1 > target:
		_dispose(_stack.pop_back() as Control)
	_show_screen(_stack.back() as Control)

func _push_new(name: String) -> void:
	var scr := _make(name)
	_stack.append(scr)
	if not scr.is_inside_tree():
		add_child(scr)
	_show_screen(scr)

func _find_stack_index(name: String) -> int:
	for index in range(_stack.size() - 1, -1, -1):
		var scr = _stack[index]
		if scr is Control and is_instance_valid(scr) \
				and scr.get_meta("screen_name", "") == name:
			return index
	return -1

func _hide_screen(scr: Control) -> void:
	if not is_instance_valid(scr):
		return
	scr.hide()
	scr.process_mode = Node.PROCESS_MODE_DISABLED

func _show_screen(scr: Control) -> void:
	if not is_instance_valid(scr):
		return
	var was_entered := bool(scr.get_meta("mgr_entered", false))
	scr.process_mode = Node.PROCESS_MODE_INHERIT
	scr.show()
	if was_entered and scr.has_method("on_enter"):
		scr.call("on_enter")
	scr.set_meta("mgr_entered", true)

func _dispose(scr: Control) -> void:
	NODE_HELPER.dispose(scr)

func is_generation_current(generation: int) -> bool:
	return generation == navigation_generation

func _make(name: String) -> Control:
	var scr: Control
	match name:
		"server_discovery": scr = preload("res://src/screens/SServerDiscovery.tscn").instantiate()
		"class_select":     scr = preload("res://src/screens/SClassSelect.tscn").instantiate()
		"name_input":       scr = preload("res://src/screens/SNameInput.tscn").instantiate()
		"main_menu":        scr = preload("res://src/screens/SMainMenu.tscn").instantiate()
		"checkout":         scr = preload("res://src/screens/SCheckout.tscn").instantiate()
		"return_scan":      scr = preload("res://src/screens/SReturnScan.tscn").instantiate()
		"search":           scr = preload("res://src/screens/SSearch.tscn").instantiate()
		"hold_ready":       scr = preload("res://src/screens/SHoldReady.tscn").instantiate()
		"book_detail":      scr = preload("res://src/screens/SBookDetail.tscn").instantiate()
		"my_holds":         scr = preload("res://src/screens/SMyHolds.tscn").instantiate()
		"settings":         scr = preload("res://src/screens/SSettings.tscn").instantiate()
		_:
			push_error("Unknown screen: " + name)
			scr = Control.new()

	scr.set_meta("screen_name", name)
	scr.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

	# CanvasLayer blocks theme inheritance, so apply the active theme explicitly.
	scr.theme = get_tree().root.theme
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
