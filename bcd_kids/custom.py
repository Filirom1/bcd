# custom.py — lu automatiquement par SCons à la compilation de Godot
# Optimisé pour BCD Kids : UI 2D pure, HTTP, JSON, pas d'audio ni de 3D

target        = "template_release"
debug_symbols = "no"
optimize      = "size"
lto           = "none"   # Désactivé pour CI (thin LTO nécessite LLVM, pas disponible sur GitHub Actions)

# ─── Rendu ─────────────────────────────────────────────────────────────────
disable_3d   = "yes"   # Aucune 3D dans le projet
vulkan       = "no"    # GL Compatibility uniquement
d3d12        = "no"    # Pas de Direct3D 12 (OpenGL uniquement)
use_volk     = "no"
openxr       = "no"

# ─── GUI ───────────────────────────────────────────────────────────────────
# NOTE: OptionButton is needed for FilterPanel, so we can't disable advanced GUI entirely
# disable_advanced_gui = "yes"   # Would disable Tree, ItemList, TextEdit, OptionButton, etc.

# ─── Divers ────────────────────────────────────────────────────────────────
minizip    = "no"
deprecated = "no"

# ─── Modules : on part de zéro ─────────────────────────────────────────────
modules_enabled_by_default = "no"

# ✅ GDScript — seul langage utilisé
module_gdscript_enabled = "yes"

# ✅ Rendu texte léger (anglais uniquement, pas de RTL/arabe/hébreu)
module_text_server_fb_enabled  = "yes"
module_text_server_adv_enabled = "no"

# ✅ Polices (requis par le text server)
module_freetype_enabled = "yes"

# ✅ TLS/HTTPS pour les appels API (HTTPRequest)
module_mbedtls_enabled = "yes"

# ✅ Images PNG (fonds d'écran, couvertures de livres)
module_png_enabled             = "yes"
module_jpg_enabled             = "yes"

# ❌ Formats non utilisés
module_webp_enabled            = "no"
module_basis_universal_enabled = "no"
module_svg_enabled             = "no"

# ❌ Pas d'audio
module_vorbis_enabled  = "no"
module_minimp3_enabled = "no"
module_opus_enabled    = "no"
module_theora_enabled  = "no"

# ❌ Pas de physique
module_godot_physics_2d_enabled = "no"
module_godot_physics_3d_enabled = "no"

# ❌ Pas de réseau avancé
module_websocket_enabled = "no"
module_jsonrpc_enabled   = "no"