# Charte graphique de l'interface web

Cette charte est la référence visuelle de l'interface web BCD. Elle vise une
interface claire, accueillante et légèrement ludique, sans modifier les parcours
ni ajouter d'écrans. Elle s'applique aux pages, composants partagés et modales.

## Sources de vérité

- Les valeurs visuelles partagées sont définies dans
  [`theme.css`](../src/bcd_web_vue/css/theme.css).
- Les styles communs et les valeurs Bootstrap associées sont appliqués dans
  [`main.css`](../src/bcd_web_vue/css/main.css).
- Les composants JavaScript qui dessinent dans un canvas lisent les tokens avec
  [`colors.js`](../src/bcd_web_vue/js/utils/colors.js), car le canvas ne résout
  pas les variables CSS (couleurs, tailles et rayons).

Un changement de style partagé commence par un token, pas par une nouvelle
valeur locale. Si une nouvelle valeur sémantique est nécessaire, elle est ajoutée
à `theme.css` et décrite ici. Les deux éditions linguistiques et les flux métier
restent inchangés.

## Palette

| Rôle | Token | Valeur actuelle |
|---|---|---|
| Action principale et liens | `--bcd-primary` | `#0284c7` |
| Survol principal | `--bcd-primary-hover` | `#0369a1` |
| Fond de sélection | `--bcd-primary-subtle` / `--bcd-selection` | `#e0f2fe` |
| Succès / disponible | `--bcd-success` | `#10b981` |
| Avertissement / réservé | `--bcd-warning` | `#f59e0b` |
| Erreur / indisponible | `--bcd-danger` | `#ef4444` |
| Information | `--bcd-info` | `#06b6d4` |
| Fond général | `--bcd-bg` | `#f7faff` |
| Surface et navigation | `--bcd-surface`, `--bcd-sidebar` | `#ffffff` |
| Texte principal | `--bcd-text-main` | `#1f2937` |
| Texte secondaire | `--bcd-text-muted` | `#6b7280` |
| Bordure standard / forte | `--bcd-border` / `--bcd-border-strong` | `#e5e7eb` / `#cbd5e1` |

Les états ont toujours un libellé ou une icône en complément de leur couleur.
Les couleurs de graphiques viennent de `--bcd-chart-*`; elles servent à
distinguer des séries et ne remplacent pas les couleurs sémantiques de statut.
Le chargement, les ombres, les squelettes et les fonds superposés utilisent
aussi des tokens.

Les couleurs saisies ou configurées par les bibliothécaires (par exemple les
couleurs Dewey ou d'emplacement) sont des données, pas la palette de l'interface.
Elles peuvent donc varier. Les couleurs d'impression sont définies séparément
pour rester lisibles sur papier.

## Typographie

- Famille : pile système identique pour le corps et les titres (`--font-body`,
  `--font-heading`).
- Taille racine : `16px`; corps courant : `--bcd-font-size-base` (`0.875rem`,
  soit 14px).
- Échelle : `xs` 12px, `sm` 13px, `base` 14px, `lg` 16px, `xl` 20px,
  titre de section 24px, sous-titre 18px, titre de page 28px et titre de marque
  40px sur l'écran de chargement.
- Les libellés de graphiques peuvent utiliser `--bcd-font-size-chart` (11px)
  lorsqu'ils sont visuels et secondaires. Le texte fonctionnel ne descend pas
  sous `xs`.
- Le corps conserve une interligne de `1.6`; les titres partagent la même
  famille et une graisse modérée. Le gras sert à la hiérarchie, pas à décorer
  chaque libellé.

Employer les tokens `--bcd-font-size-*` pour le texte. Les dimensions d'icônes,
illustrations, confettis et autres éléments décoratifs peuvent être spécifiques;
elles ne doivent pas réduire la taille du texte associé.

## Espacement et formes

- Utiliser l'échelle `--bcd-space-1` à `--bcd-space-6` pour les nouveaux
  espacements partagés.
- Les cartes, champs, boutons, menus et modales ont des angles discrets :
  `--bcd-radius-sm` (4px) par défaut et `--bcd-radius-md` (6px) pour une surface
  plus importante.
- Les badges et contrôles ne prennent pas une forme pilule par défaut.
  `--bcd-radius-pill` et le cercle sont réservés aux indicateurs réellement
  circulaires (points, avatars, curseurs) ou aux éléments qui doivent être
  distingués comme tels.
- Les ombres proviennent de `--bcd-shadow-sm`, `--bcd-shadow-md`,
  `--bcd-shadow-lg`, `--bcd-shadow-control`, `--bcd-shadow-overlay`,
  `--bcd-shadow-focus` ou `--bcd-shadow-primary`.

## Composants et états

- Boutons, champs, tableaux, cartes, badges, menus et modales héritent des
  couleurs, tailles et rayons partagés; les modales ne recréent pas leur propre
  système typographique.
- Une action principale est visuellement identifiable par le bleu principal.
  Les actions de succès, d'avertissement et de danger emploient les couleurs
  sémantiques correspondantes.
- Les tableaux privilégient une lecture dense mais confortable : texte courant
  au minimum à `base`, en-têtes clairement identifiés et contraste de bordure
  suffisant.
- Les animations restent brèves et non bloquantes. Une animation décorative ne
  doit pas empêcher l'usage; respecter `prefers-reduced-motion` lorsqu'elle
  s'applique.

## Accessibilité et adaptation

- Garder un contraste lisible entre texte et surface; ne pas transmettre une
  information par la seule couleur.
- Conserver un indicateur de focus visible pour la navigation clavier et ne pas
  supprimer les comportements natifs sans alternative accessible.
- Le texte fonctionnel doit rester lisible en zoom; éviter les tailles fixes
  qui provoquent un débordement ou une coupure.
- Les pages s'adaptent aux petites fenêtres sans changer de parcours. Un contenu
  naturellement large (comme la chronologie) peut défiler horizontalement dans
  son propre conteneur, pas dans toute la page.

## Exceptions documentées

1. `print-labels.css` et les règles `@media print` peuvent employer des couleurs,
   traits et tailles adaptés au papier noir et blanc.
2. Les palettes personnalisables (Dewey, emplacements et autres données
   utilisateur) ne sont pas remplacées par les couleurs de l'interface.
3. Les couleurs/transparences dérivées d'un état dynamique ou d'une série de
   graphique peuvent être calculées, mais doivent partir d'un token ou d'une
   donnée métier clairement identifiée.
4. Les dimensions d'icônes, couvertures et décorations ne sont pas des tailles
   de texte. La dimension décorative ne justifie pas une forme arrondie pour les
   surfaces fonctionnelles.

## Faire évoluer le thème

1. Modifier ou ajouter les tokens dans `theme.css` avec un nom décrivant leur
   rôle, pas leur apparence ponctuelle.
2. Mettre à jour ce document si la règle ou la valeur de référence change.
3. Remplacer les valeurs locales redondantes par les tokens; conserver les
   exceptions ci-dessus uniquement lorsqu'elles sont nécessaires.
4. Vérifier les pages et modales représentatives, puis lancer `npm run
   type-check`, `npm run build:web`, les tests JavaScript concernés et
   `git diff --check`.
