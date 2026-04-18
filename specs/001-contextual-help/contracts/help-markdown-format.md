# Contract: Help Markdown File Format

**Version**: 1.0
**Applies to**: All files in `src/bcd_web_vue/help/fr/` and `src/bcd_web_vue/help/en/`

---

## File Structure

Each help file MUST follow this structure:

```markdown
# [Section Title]

[One-sentence summary of what this page does, ≤ 20 words]

---

## Étape 1 — [Action Title]  (or "Step 1 —" in EN)

[Explanation in plain language. Max 3 sentences. No technical jargon.]

![Alt text describing the screenshot](/static/help/images/{section}-{nn}-{state}.png)

> **Conseil :** [Optional tip in a blockquote. Use "Tip:" in EN]

## Étape 2 — [Action Title]

[Explanation]

![Alt text](/static/help/images/{section}-{nn}-{state}.png)

---

## Problèmes fréquents  (or "Common Issues" in EN)

| Problème | Solution |
|----------|----------|
| [User-visible symptom] | [Action to take] |
```

---

## Rules

### Content
- Steps MUST be numbered sequentially starting at 1
- Each step MUST have a title starting with the step number
- Each major step SHOULD have a screenshot
- Screenshots MUST use absolute HTTP paths: `/static/help/images/...`
- Blockquote tips (`> **Conseil :**`) are optional but encouraged for non-obvious actions
- "Problèmes fréquents" section is mandatory (at least 2 rows)
- Maximum 8 steps per section (keep it concise)

### Language
- FR: Use "tu" form (informal) for instructions ("Clique sur…", "Tape le numéro…")
  - Exception: Use "vous" for "Bienvenue" and formal intro if present
- EN: Use imperative form ("Click on…", "Type the number…")
- Avoid technical terms: no "URL", "API", "modal", "component"
- Dates shown as day/month/year (FR), month/day/year (EN)

### Images
- Image path format: `/static/help/images/{section_id}-{nn:02d}-{state}.png`
- Alt text MUST describe what is shown (not "screenshot")
- Images MUST exist before help files reference them

### Headings
- `#` (H1): Section title — exactly one, at top of file
- `##` (H2): Step headings — numbered
- `###` (H3): Sub-steps if needed (rare)
- Never use H4 or deeper

### Separators
- `---` (horizontal rule) before "Problèmes fréquents" and between major groups
- One blank line between paragraphs

---

## Example: emprunter.md (FR)

```markdown
# Emprunter des livres

Utilisez cette page pour prêter un ou plusieurs livres à un élève ou enseignant.

---

## Étape 1 — Saisir le numéro d'emprunteur

Tape ou scanne le numéro de l'élève dans le champ « Numéro d'emprunteur ».
La fiche de l'élève s'affiche automatiquement.

![Page d'emprunt vide avec le champ numéro d'emprunteur](/static/help/images/checkout-01-empty.png)

> **Conseil :** Tu peux utiliser une douchette (scanner de codes-barres) pour scanner
> directement la carte de l'élève.

## Étape 2 — Scanner les livres

Scanne le code-barres de chaque livre à emprunter.
Chaque livre ajouté apparaît dans la liste.

![Fiche élève chargée avec un livre dans la liste](/static/help/images/checkout-03-item-scanned.png)

## Étape 3 — Confirmer l'emprunt

Clique sur **« Confirmer l'emprunt »**.
La date de retour est calculée automatiquement (14 jours par défaut).

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| « Limite de livres atteinte » | L'élève a déjà le nombre maximum de livres autorisé. Il doit en rendre un avant d'en emprunter un nouveau. |
| « Livre déjà emprunté » | Ce livre est actuellement chez un autre élève. Propose-lui un autre exemplaire ou note la réservation. |
| Le numéro d'élève n'est pas reconnu | Vérifie que le format est correct (ex: 12345) ou cherche l'élève dans la liste des emprunteurs. |
```
