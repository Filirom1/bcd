# Retourner des livres

Cette page permet d'enregistrer le retour d'un ou plusieurs livres empruntés.

---

## Étape 1 — Scanner le code-barres du livre

Scanner directement le code-barres du livre à retourner.
Le retour est enregistré immédiatement, sans avoir à identifier l'emprunteur au préalable.

![Page de retour avec le champ de scan actif](../images/return-01-empty.png)

> **Conseil :** Les livres peuvent être scannés les uns après les autres sans aucune manipulation entre chaque scan.

## Étape 2 — Vérifier le résumé de retour

Chaque livre retourné apparaît dans la liste à droite de l'écran.
La liste indique le titre, le numéro d'inventaire et l'heure de retour.

![Liste des retours de la session en cours](../images/return-02-item-returned.png)

> **Conseil :** Si un livre était en retard, un badge rouge « Retard » s'affiche dans la liste.
> L'emprunteur n'est pas bloqué automatiquement : la décision revient au personnel de la bibliothèque.

> **Conseil :** Pour consulter la situation complète d'un élève (prêts en cours, retards), accéder à la page **Emprunteurs** depuis le menu et rechercher l'élève par nom ou identifiant.

---

## Retour via BCD Kids (client élève)

Les élèves peuvent aussi enregistrer eux-mêmes le retour de leurs livres depuis le **client BCD Kids**.
Le client affiche un écran de retour simple : l'élève scanne son code-barres ou saisit son identifiant,
puis scanne le code-barres du livre à retourner.

Le retour est enregistré immédiatement dans la même base que celle de la bibliothèque —
aucune action supplémentaire n'est nécessaire de la part de l'enseignant.

> **Remarque :** Si le livre est rendu à quelqu'un d'autre que l'emprunteur (un camarade rapporte
> le livre d'un absent), il est préférable d'utiliser la page de retour ci-dessus (accès enseignant),
> car elle ne demande pas d'identifier l'emprunteur.

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| Le code-barres n'est pas reconnu | Vérifier que le préfixe d'article est bien configuré dans les paramètres, ou saisir le numéro d'inventaire manuellement. |
| « Article non emprunté » | Ce livre n'est pas actuellement sorti. Vérifier le numéro d'inventaire. |
| Le retard n'est pas affiché | Le retard s'affiche seulement si la date de retour prévue est dépassée. Vérifier la date système. |
