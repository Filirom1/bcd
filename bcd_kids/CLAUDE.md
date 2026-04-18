# CLAUDE.md — bcd_kids (Godot client)

# English

Code and comment in english

## Règles UI fondamentales

**Chaque élément d'interface doit avoir son propre fichier `.tscn`.**

**L'UI doit être minimaliste et fonctionnelle.** Pas de fioritures, pas d'animations complexes, pas de mise en page élaborée. Le propriétaire du projet ajuste lui-même les tailles, marges, couleurs et positionnements dans l'éditeur Godot. Claude fournit une base propre et sobre — rien de plus.

Le propriétaire du projet ajuste le positionnement, les tailles et les marges directement dans l'éditeur Godot. Si un composant n'existe qu'en GDScript procédural, il est impossible à ajuster visuellement.

### Ce que ça implique concrètement

- Tout composant réutilisable → `components/NomDuComposant.tscn` + `components/NomDuComposant.gd`
- Tout écran → `src/screens/SNomEcran.tscn` + `src/screens/SNomEcran.gd`
- Le `.gd` contient uniquement la logique (signaux, données, appels API)
- Le `.tscn` contient toute la structure visuelle (layout, tailles, couleurs, textures)
- **Zéro construction d'UI procédurale** dans les `.gd` des écrans (pas de `Node.new()`, `add_child()` pour construire la mise en page)

### Principe DRY pour les ressources partagées

**Ne jamais dupliquer les références de ressources dans chaque `.tscn`.**

- **Police** : définie une seule fois dans `theme.tres`. Chaque scène applique `theme = ExtResource("theme.tres")` sur son nœud racine. Les Labels héritent automatiquement — **pas de `theme_override_fonts/font`** sur chaque Label.
- **Taille et couleur** : les seules surcharges autorisées sur les Labels individuels sont `theme_override_font_sizes/font_size` et `theme_override_colors/font_color` quand elles diffèrent du défaut.
- **Textures** : toujours passer par le .tscn, jamais référencer un png directement dans une scène.
- **NinePatch panels** : utiliser `PanelContainer` + `StyleBoxTexture` (sub-resource inline dans le `.tscn`) plutôt que `NinePatchRect` — le `PanelContainer` s'agrandit avec son contenu.
