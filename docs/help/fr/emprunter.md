# Emprunter des livres

Cette page permet de prêter un ou plusieurs livres à un élève ou à un enseignant.

---

## Étape 1 — Saisir le numéro d'emprunteur

Saisir ou scanner le numéro de l'élève dans le champ « Numéro d'emprunteur ».
La fiche de l'élève s'affiche automatiquement avec ses emprunts en cours.

![Page d'emprunt vide avec le champ numéro d'emprunteur](../images/checkout-01-empty.png)

> **Conseil :** Une douchette (scanner de codes-barres) peut être utilisée pour scanner directement la carte de l'élève.

## Étape 2 — Vérifier la fiche de l'élève

Vérifier le nom, la classe et le nombre de livres déjà empruntés.
Un badge rouge indique que l'élève a atteint la limite ou a des retards.

![Fiche élève chargée avec compteur d'emprunts](../images/checkout-02-borrower-loaded.png)

> **Conseil :** Si l'élève a des livres en retard, ils apparaissent en rouge dans la liste de ses emprunts.

## Étape 3 — Scanner les livres

Scanner le code-barres de chaque livre à emprunter.
Chaque livre ajouté apparaît dans la liste en haut de l'écran.

![Fiche élève chargée avec un livre dans la liste](../images/checkout-03-item-scanned.png)

## Étape 4 — Confirmer l'emprunt

L'emprunt est enregistré automatiquement dès que le code-barres est scanné.
La date de retour est calculée automatiquement selon les paramètres de la bibliothèque.

![Confirmation d'emprunt réussi](../images/checkout-04-confirmed.png)

> **Conseil :** Pour changer d'élève, cliquer sur la liste de classe à gauche ou saisir un nouveau numéro d'emprunteur.

---

## Emprunt via BCD Kids (client élève)

Les élèves peuvent aussi **emprunter eux-mêmes** leurs livres depuis le **client BCD Kids**,
sans intervention de l'enseignant.

Workflow dans BCD Kids :
1. L'élève sélectionne sa classe puis son nom
2. Il scanne le code-barres du livre (ou plusieurs livres)
3. L'emprunt est enregistré immédiatement dans la bibliothèque

Les prêts effectués depuis BCD Kids apparaissent normalement dans la page Emprunter et
dans la fiche de chaque élève — tout est synchronisé en temps réel.

> **Conseil :** BCD Kids est conçu pour les enfants de 6 à 11 ans. Pour les enseignants ou
> pour des opérations de lot (plusieurs élèves à la suite), la page « Emprunter » de BCD reste
> plus rapide.

---

## Problèmes fréquents

| Problème | Solution |
|----------|----------|
| « Limite de livres atteinte » | L'élève a déjà le nombre maximum de livres autorisé. Il doit en rendre un avant d'en emprunter un nouveau. |
| « Livre déjà emprunté » | Ce livre est actuellement chez un autre élève. Proposer un autre exemplaire ou noter la réservation. |
| Le numéro d'élève n'est pas reconnu | Vérifier que le format est correct (ex : 12345) ou chercher l'élève dans la liste des emprunteurs. |
| Le code-barres du livre ne fonctionne pas | Saisir le numéro d'inventaire manuellement dans le champ de scan. |
