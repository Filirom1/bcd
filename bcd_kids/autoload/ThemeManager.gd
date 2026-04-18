# Autoload "ThemeManager" - Active theme + color palette
extends Node

signal theme_changed

const THEMES := {
	"forest": {
		"label_fr": "Foret enchantee",
		"label_en": "Enchanted Forest",
		"tres": "res://themes/forest.tres",
		"background": "res://assets/images/backgrounds/forest.png"
	},
	"lego": {
		"label_fr": "LEGO",
		"label_en": "LEGO",
		"tres": "res://themes/lego.tres",
		"background": "res://assets/images/backgrounds/lego.png"
	},
	"licorne": {
		"label_fr": "Licorne",
		"label_en": "Unicorn",
		"tres": "res://themes/licorne.tres",
		"background": "res://assets/images/backgrounds/licorne.png"
	},
	"minecraft": {
		"label_fr": "Minecraft",
		"label_en": "Minecraft",
		"tres": "res://themes/minecraft.tres",
		"background": "res://assets/images/backgrounds/minecraft.png"
	},
	"pokemon": {
		"label_fr": "Pokemon",
		"label_en": "Pokemon",
		"tres": "res://themes/pokemon.tres",
		"background": "res://assets/images/backgrounds/pokemon.png"
	},
	"barbie": {
		"label_fr": "Barbie",
		"label_en": "Barbie",
		"tres": "res://themes/barbie.tres",
		"background": "res://assets/images/backgrounds/barbie.png"
	},
	"manga": {
		"label_fr": "Manga",
		"label_en": "Manga",
		"tres": "res://themes/manga.tres",
		"background": "res://assets/images/backgrounds/manga.png"
	},
	"vaiana": {
		"label_fr": "Vaiana",
		"label_en": "Moana",
		"tres": "res://themes/vaiana.tres",
		"background": "res://assets/images/backgrounds/vaiana.png"
	},
	"reine-des-neiges": {
		"label_fr": "Reine des Neiges",
		"label_en": "Frozen",
		"tres": "res://themes/reine-des-neiges.tres",
		"background": "res://assets/images/backgrounds/reine-des-neiges.png"
	},
	"asterix": {
		"label_fr": "Asterix",
		"label_en": "Asterix",
		"tres": "res://themes/asterix.tres",
		"background": "res://assets/images/backgrounds/asterix.png"
	},
	"one-piece": {
		"label_fr": "One Piece",
		"label_en": "One Piece",
		"tres": "res://themes/one-piece.tres",
		"background": "res://assets/images/backgrounds/one-piece.png"
	},
	"toy-story": {
		"label_fr": "Toy Story",
		"label_en": "Toy Story",
		"tres": "res://themes/toy-story.tres",
		"background": "res://assets/images/backgrounds/toy-story.png"
	},
	"coco": {
		"label_fr": "Coco",
		"label_en": "Coco",
		"tres": "res://themes/coco.tres",
		"background": "res://assets/images/backgrounds/coco.png"
	},
	"mortelle-adele": {
		"label_fr": "Mortelle Adele",
		"label_en": "Mortelle Adele",
		"tres": "res://themes/mortelle-adele.tres",
		"background": "res://assets/images/backgrounds/mortelle-adele.png"
	},
	"cars": {
		"label_fr": "Cars",
		"label_en": "Cars",
		"tres": "res://themes/cars.tres",
		"background": "res://assets/images/backgrounds/cars.png"
	},
	"ratatouille": {
		"label_fr": "Ratatouille",
		"label_en": "Ratatouille",
		"tres": "res://themes/ratatouille.tres",
		"background": "res://assets/images/backgrounds/ratatouille.png"
	},
	"peter-pan": {
		"label_fr": "Peter Pan",
		"label_en": "Peter Pan",
		"tres": "res://themes/peter-pan.tres",
		"background": "res://assets/images/backgrounds/peter-pan.png"
	},
	"mulan": {
		"label_fr": "Mulan",
		"label_en": "Mulan",
		"tres": "res://themes/mulan.tres",
		"background": "res://assets/images/backgrounds/mulan.png"
	},
	"pirate": {
		"label_fr": "Pirate",
		"label_en": "Pirate",
		"tres": "res://themes/pirate.tres",
		"background": "res://assets/images/backgrounds/pirate.png"
	},
	"belle-et-la-bete": {
		"label_fr": "Belle et la Bete",
		"label_en": "Beauty and the Beast",
		"tres": "res://themes/belle-et-la-bete.tres",
		"background": "res://assets/images/backgrounds/belle-et-la-bete.png"
	},
	"chaperon-rouge": {
		"label_fr": "Chaperon Rouge",
		"label_en": "Little Red Riding Hood",
		"tres": "res://themes/chaperon-rouge.tres",
		"background": "res://assets/images/backgrounds/chaperon-rouge.png"
	},
	"sorciere": {
		"label_fr": "Sorciere",
		"label_en": "Witch",
		"tres": "res://themes/sorciere.tres",
		"background": "res://assets/images/backgrounds/sorciere.png"
	},
	"anatole": {
		"label_fr": "Anatole",
		"label_en": "Anatole",
		"tres": "res://themes/anatole.tres",
		"background": "res://assets/images/backgrounds/anatole.png"
	},
	"bd": {
		"label_fr": "Bande Dessinee",
		"label_en": "Comics",
		"tres": "res://themes/bd.tres",
		"background": "res://assets/images/backgrounds/bd.png"
	},
	"chiens-pirates": {
		"label_fr": "Chiens Pirates",
		"label_en": "Pirate Dogs",
		"tres": "res://themes/chiens-pirates.tres",
		"background": "res://assets/images/backgrounds/chiens-pirates.png"
	},
	"chi": {
		"label_fr": "Chi",
		"label_en": "Chi",
		"tres": "res://themes/chi.tres",
		"background": "res://assets/images/backgrounds/chi.png"
	},
	"cornebidouille": {
		"label_fr": "Cornebidouille",
		"label_en": "Cornebidouille",
		"tres": "res://themes/cornebidouille.tres",
		"background": "res://assets/images/backgrounds/cornebidouille.png"
	},
	"duplo": {
		"label_fr": "LEGO Duplo",
		"label_en": "LEGO Duplo",
		"tres": "res://themes/duplo.tres",
		"background": "res://assets/images/backgrounds/duplo.png"
	},
	"lego2": {
		"label_fr": "LEGO 2",
		"label_en": "LEGO 2",
		"tres": "res://themes/lego2.tres",
		"background": "res://assets/images/backgrounds/lego2.png"
	},
	"les-sisters": {
		"label_fr": "Les Sisters",
		"label_en": "Les Sisters",
		"tres": "res://themes/les-sisters.tres",
		"background": "res://assets/images/backgrounds/les-sisters.png"
	},
	"mortelle-adele2": {
		"label_fr": "Mortelle Adele 2",
		"label_en": "Mortelle Adele 2",
		"tres": "res://themes/mortelle-adele2.tres",
		"background": "res://assets/images/backgrounds/mortelle-adele2.png"
	},
	"ponti": {
		"label_fr": "Ponti",
		"label_en": "Ponti",
		"tres": "res://themes/ponti.tres",
		"background": "res://assets/images/backgrounds/ponti.png"
	},
	"ponti2": {
		"label_fr": "Ponti 2",
		"label_en": "Ponti 2",
		"tres": "res://themes/ponti2.tres",
		"background": "res://assets/images/backgrounds/ponti2.png"
	},
	"toto": {
		"label_fr": "Toto",
		"label_en": "Toto",
		"tres": "res://themes/toto.tres",
		"background": "res://assets/images/backgrounds/toto.png"
	},
	"popup": {
		"label_fr": "Livres Pop-Up",
		"label_en": "Pop-Up Books",
		"tres": "res://themes/popup.tres",
		"background": "res://assets/images/backgrounds/popup.png"
	},
	"bcd": {
		"label_fr": "Bibliotheque",
		"label_en": "Library",
		"tres": "res://themes/bcd.tres",
		"background": "res://assets/images/backgrounds/bcd.png"
	},
	"bcd2": {
		"label_fr": "Bibliotheque 2",
		"label_en": "Library 2",
		"tres": "res://themes/bcd2.tres",
		"background": "res://assets/images/backgrounds/bcd2.png"
	},
	":random": {
		"label_fr": "Aleatoire",
		"label_en": "Random",
		"tres": "",
		"background": ""
	}
}

var current_theme_name: String = "forest"
var background_texture: Texture2D = null

# Color palette (fallback placeholders - actual values loaded from theme)
var BG              := Color.WHITE
var BG_GRADIENT_END := Color.WHITE
var BG_WHITE        := Color.WHITE
var BG_BUTTON_HOVER := Color.WHITE
var BG_DARK_OVERLAY := Color.BLACK
var TEXT            := Color.BLACK
var TEXT_LIGHT      := Color.BLACK
var TEXT_GRAY_LIGHT := Color.BLACK
var TEXT_GRAY_MEDIUM:= Color.BLACK
var TEXT_DARK       := Color.BLACK
var PRIMARY         := Color.BLACK
var SECONDARY       := Color.BLACK
var ACCENT          := Color.BLACK
var SUCCESS         := Color.BLACK
var ERROR           := Color.BLACK
var WARNING         := Color.BLACK
var INFO            := Color.BLACK
var AVAILABLE       := Color.BLACK
var ON_LOAN         := Color.BLACK
var RESERVED        := Color.BLACK
var NEUTRAL         := Color.BLACK
var BORDER          := Color.BLACK

func _ready() -> void:
	set_theme("forest")

func set_theme(name: String) -> void:
	if name == ":random":
		var real_keys := THEMES.keys().filter(func(k): return k != ":random")
		name = real_keys[randi() % real_keys.size()]
	if not THEMES.has(name):
		push_error("ThemeManager: unknown theme: " + name)
		return
	current_theme_name = name
	var cfg: Dictionary = THEMES[name]
	var t := load(cfg["tres"]) as Theme
	if not t:
		push_error("ThemeManager: failed to load theme: " + cfg["tres"])
		return
	get_tree().root.theme = t
	_load_colors(t)
	background_texture = load(cfg["background"]) as Texture2D
	theme_changed.emit()

func _load_colors(t: Theme) -> void:
	if t.has_color("bg",              "BCD"): BG              = t.get_color("bg",              "BCD")
	if t.has_color("bg_gradient_end", "BCD"): BG_GRADIENT_END = t.get_color("bg_gradient_end", "BCD")
	if t.has_color("bg_white",        "BCD"): BG_WHITE        = t.get_color("bg_white",        "BCD")
	if t.has_color("bg_button_hover", "BCD"): BG_BUTTON_HOVER = t.get_color("bg_button_hover", "BCD")
	if t.has_color("bg_dark_overlay", "BCD"): BG_DARK_OVERLAY = t.get_color("bg_dark_overlay", "BCD")
	if t.has_color("text",            "BCD"): TEXT            = t.get_color("text",            "BCD")
	if t.has_color("text_light",      "BCD"): TEXT_LIGHT      = t.get_color("text_light",      "BCD")
	if t.has_color("text_gray_light", "BCD"): TEXT_GRAY_LIGHT = t.get_color("text_gray_light", "BCD")
	if t.has_color("text_gray_medium","BCD"): TEXT_GRAY_MEDIUM= t.get_color("text_gray_medium","BCD")
	if t.has_color("text_dark",       "BCD"): TEXT_DARK       = t.get_color("text_dark",       "BCD")
	if t.has_color("primary",         "BCD"): PRIMARY         = t.get_color("primary",         "BCD")
	if t.has_color("secondary",       "BCD"): SECONDARY       = t.get_color("secondary",       "BCD")
	if t.has_color("accent",          "BCD"): ACCENT          = t.get_color("accent",          "BCD")
	if t.has_color("success",         "BCD"): SUCCESS         = t.get_color("success",         "BCD")
	if t.has_color("error",           "BCD"): ERROR           = t.get_color("error",           "BCD")
	if t.has_color("warning",         "BCD"): WARNING         = t.get_color("warning",         "BCD")
	if t.has_color("info",            "BCD"): INFO            = t.get_color("info",            "BCD")
	if t.has_color("available",       "BCD"): AVAILABLE       = t.get_color("available",       "BCD")
	if t.has_color("on_loan",         "BCD"): ON_LOAN         = t.get_color("on_loan",         "BCD")
	if t.has_color("reserved",        "BCD"): RESERVED        = t.get_color("reserved",        "BCD")
	if t.has_color("neutral",         "BCD"): NEUTRAL         = t.get_color("neutral",         "BCD")
	if t.has_color("border",          "BCD"): BORDER          = t.get_color("border",          "BCD")

# ============================================================================
# Animation utilities (moved from BCDTheme)
# ============================================================================

static func animate_pop_in(node: Control) -> void:
	node.scale = Vector2(0.5, 0.5)
	node.modulate.a = 0.0
	var tween = node.create_tween()
	tween.set_ease(Tween.EASE_OUT)
	tween.set_trans(Tween.TRANS_BACK)
	tween.parallel().tween_property(node, "scale", Vector2(1.0, 1.0), 0.4)
	tween.parallel().tween_property(node, "modulate:a", 1.0, 0.3)

static func animate_success_flash(node: Control) -> void:
	var original_color := node.modulate
	var tween := node.create_tween()
	tween.tween_property(node, "modulate", ThemeManager.SUCCESS, 0.1)
	tween.tween_property(node, "modulate", original_color, 0.3)

static func animate_error_shake(node: Control) -> void:
	var original_pos := node.position
	var tween := node.create_tween()
	for i in range(3):
		tween.tween_property(node, "position:x", original_pos.x + 10, 0.05)
		tween.tween_property(node, "position:x", original_pos.x - 10, 0.05)
	tween.tween_property(node, "position", original_pos, 0.05)
