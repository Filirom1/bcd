# Themes

## Font selection

Each theme should have a font that reinforces its visual identity. When creating a new theme:

1. **Check existing fonts first** — reuse one if it fits the aesthetic (see table below)
2. **Download a new one if not** — pick from Google Fonts (SIL OFL license), download via:
   ```
   curl -L "https://github.com/google/fonts/raw/main/ofl/<folder>/<FontName>.ttf" -o assets/fonts/<FontName>.ttf
   ```
3. **Open the project in Godot editor once** before running — it auto-imports the `.ttf` and creates the `.import` file. Without this step, Godot throws a FreeType error at runtime.
4. **Reference without uid** in the `.tres` (Godot will resolve by path on first import):
   ```
   [ext_resource type="FontFile" path="res://assets/fonts/<FontName>.ttf" id="2_custom"]
   ```
5. **Keep inputs on Nunito Regular** (`LineEdit/fonts/font = ExtResource("1_regular")`) unless the display font is also readable at small sizes when typed.
6. **Always add `LineEdit/styles/normal` and `LineEdit/styles/focus`** explicitly in the `[resource]` section — otherwise Godot falls back to its default dark style.

### Font ideas by theme type

| Theme style | Suggested fonts |
|---|---|
| Playful / kids | Fredoka One, Baloo 2, Nunito Bold |
| Fantasy / magic | MedievalSharp, Cinzel, Uncial Antiqua |
| Pixel / retro | Press Start 2P, VT323, Silkscreen |
| Bold / action | Bangers, Boogaloo, Righteous |
| Soft / dreamy | Pacifico, Comfortaa, Quicksand |
| Nature / adventure | Josefin Sans, Raleway, Cabin |

## Available fonts

Only use fonts that already have a `.import` file in `assets/fonts/` — otherwise Godot will throw a FreeType error at runtime.

| File | uid | Usage |
|---|---|---|
| `Nunito-Regular.ttf` | `uid://btekor0nv1aus` | Default body font (all themes) |
| `Nunito-Bold.ttf` | `uid://buxf5ymsb4qhq` | Bold display font (licorne theme) |
| `Bangers-Regular.ttf` | auto-imported | Display font (lego theme) |
| `PressStart2P-Regular.ttf` | auto-imported | Pixel font (minecraft theme) — tailles réduites (~14px max) |
| `Righteous-Regular.ttf` | auto-imported | Bold rounded display font (pokemon theme) |
| `Pacifico-Regular.ttf` | auto-imported | Flowing cursive display font (barbie theme) |
| `Comfortaa-Regular.ttf` | auto-imported | Rounded soft display font (reine-des-neiges theme) |
| `Boogaloo-Regular.ttf` | auto-imported | Playful tropical display font (vaiana theme) |
| `DelaGothicOne-Regular.ttf` | auto-imported | Ultra-bold dramatic display font (manga theme) |

To add a new font: drop the `.ttf` in `assets/fonts/`, open the project in Godot editor once (auto-imports it and creates the `.import` file), then reference it in your `.tres` with its uid.

## Adding a theme

1. Copy an existing `.tres` as a base: `cp kids.tres <name>.tres`
2. Add a background image: `assets/images/backgrounds/<name>.png`
3. Register in `autoload/ThemeManager.gd`:

```gdscript
"<name>": {
    "label_fr": "...",
    "label_en": "...",
    "tres": "res://themes/<name>.tres",
    "background": "res://assets/images/backgrounds/<name>.png"
}
```

The Settings screen picks up new entries automatically.

## Special theme: `:random`

The `:random` entry in `THEMES` is a meta-theme — it randomly picks one of the real themes each time it is applied. It has no `.tres` or background of its own. To trigger it from code: `ThemeManager.set_theme(":random")`.

## Customising colors

All colors are defined in the `[resource]` section under `BCD/colors/*`. These are loaded at runtime into `ThemeManager` typed variables (`ThemeManager.PRIMARY`, `ThemeManager.ERROR`, etc.).

| Key | Role |
|---|---|
| `primary` | Main accent color (buttons, titles, links) |
| `secondary` | Secondary accent |
| `accent` | Highlight / call-to-action |
| `success` / `available` | Positive state |
| `error` / `on_loan` | Negative / unavailable state |
| `warning` / `reserved` | Intermediate state |
| `info` | Informational |
| `neutral` | Muted / disabled |
| `bg` | Main background color (semi-transparent over the background image) |
| `bg_white` | Card / panel background |
| `bg_button_hover` | Button hover background |
| `bg_dark_overlay` | Modal overlay |
| `border` | Default border color |
| `text` | Body text |
| `text_light` | Secondary text |
| `text_gray_medium` / `text_gray_light` | Placeholder / disabled text |
| `text_dark` | High-contrast text |
| `text_button_hover` | Button text on hover |

When you change a `BCD/colors/*` value, also update the matching `StyleBoxFlat` sub-resources and component colors (`Button/colors/*`, `Label/colors/*`, etc.) to keep everything consistent.

### Background visibility

The `bg` alpha controls how much the background image shows through the screen overlay. The panel `bg_color` alpha controls card transparency on top of that.

| Value | Effect |
|---|---|
| `bg` alpha 0.55 | Image very visible — licorne style |
| `bg` alpha 0.72 | Balanced — image present but UI readable — lego style |
| `bg` alpha 0.92+ | Image barely visible — forest style |
| Panel alpha 0.88 | Panels slightly transparent, image shows through |
| Panel alpha 1.0 | Panels fully opaque |

## Style knobs

| Property | Effect |
|---|---|
| `border_width_*` | Thickness of borders (px). Higher = bolder look. |
| `corner_radius_*` | Roundness of corners. 0 = square, 12+ = pill. |
| `content_margin_*` | Inner padding of panels and buttons. |
| `bg_color` on `StyleBoxFlat` | Fill color of the element. |
| `border_color` on `StyleBoxFlat` | Outline color. |

## Component map

| Theme type | Used by |
|---|---|
| `Button` | All standard buttons |
| `ButtonLarge` / `ButtonSmall` / `ButtonBreadcrumb` | Size variants — set `theme_type_variation` on the node |
| `LineEdit` | Text inputs |
| `OptionButton` | Dropdowns |
| `PanelContainer` | Generic cards |
| `PanelError` / `PanelSuccess` / `PanelWarning` / `PanelInfo` / `PanelNeutral` | Semantic card variants |
| `PanelNotificationError` / `PanelNotificationSuccess` / `PanelNotificationWarning` | Toast notifications (top-strip style) |
| `Label*` variants | `LabelTitle`, `LabelSubtitle`, `LabelPrimary`, `LabelError`, `LabelSuccess`, `LabelWarning`, `LabelGrayLight`, `LabelLarge`, `LabelMedium`, `LabelSmall` |
