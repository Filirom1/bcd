# custom.py — read automatically by SCons when building Godot.
# Optimized for BCD Kids: 2D UI, HTTP, JSON, no audio or 3D.

target        = "template_release"
debug_symbols = "no"
optimize      = "size"
lto           = "none"   # Disabled for CI (thin LTO requires LLVM on GitHub Actions).

# ─── Rendering ───────────────────────────────────────────────────────────────
disable_3d   = "yes"   # No 3D in the project
vulkan       = "no"    # GL Compatibility only
d3d12        = "no"    # No Direct3D 12 (OpenGL only)
use_volk     = "no"
openxr       = "no"

# ─── GUI ───────────────────────────────────────────────────────────────────
# NOTE: OptionButton is needed for FilterPanel, so we can't disable advanced GUI entirely
# disable_advanced_gui = "yes"   # Would disable Tree, ItemList, TextEdit, OptionButton, etc.

# ─── Miscellaneous ─────────────────────────────────────────────────────────
minizip    = "no"
deprecated = "no"

# ─── Modules: start from a minimal build ─────────────────────────────────
modules_enabled_by_default = "no"

# ✅ GDScript — the only language used
module_gdscript_enabled = "yes"

# ✅ Lightweight fallback text server for Latin-script locales (English and French).
module_text_server_fb_enabled  = "yes"
module_text_server_adv_enabled = "no"

# ✅ Fonts (required by the text server)
module_freetype_enabled = "yes"

# ✅ TLS/HTTPS for API calls (HTTPRequest)
module_mbedtls_enabled = "yes"

# ✅ PNG images (backgrounds and book covers)
module_png_enabled             = "yes"
module_jpg_enabled             = "yes"
module_squish_enabled          = "yes"   # S3TC/DXT decoder (required by the export presets).

# ✅ WebP (lossless backgrounds in export mode=0)
# barichello/godot-ci generates lossless WebP rather than PNG in mode=0.
module_webp_enabled            = "yes"
module_basis_universal_enabled = "no"
module_svg_enabled             = "no"

# ❌ No audio
module_vorbis_enabled  = "no"
module_minimp3_enabled = "no"
module_opus_enabled    = "no"
module_theora_enabled  = "no"

# ❌ No physics
module_godot_physics_2d_enabled = "no"
module_godot_physics_3d_enabled = "no"

# ❌ No advanced networking
module_websocket_enabled = "no"
module_jsonrpc_enabled   = "no"