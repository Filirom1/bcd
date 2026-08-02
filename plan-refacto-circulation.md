# Plan de refactoring — domaine circulation

**Statut :** proposition à valider avant implémentation  
**Portée :** `src/bcd_api/services/circulation_service.py` et ses intégrations directes avec les réservations, emprunteurs, catalogue, inventaire et rapports.  
**Objectif :** rendre les commandes de circulation atomiques, isoler les règles métier testables sans base de données, et supprimer les duplications sans transformer les services de lecture en proxy d'un service central.

---

## 1. État initial et problèmes constatés (vérifiés dans le code source)

`circulation_service.py` (735 lignes) contient trois types de responsabilités :
- les **commandes** : prêt, retour et renouvellement ;
- les **lectures** : prêts courants et historiques paginés ;
- les **règles métier** : limites, échéances, retards, renouvellements et priorité des réservations.

Des règles liées à la circulation sont réimplémentées dans plusieurs services :

| Règle / accès | Emplacements actuels constatés |
|---|---|
| **Limite selon le rôle** (`student` vs `teacher`/`staff`) | `circulation_service.py` (checkout l.118-120), `borrower_service.py` (`enrich_borrower` l.748-751) |
| **Prêt actif** (`return_date IS NULL`) | `circulation_service.py`, `catalog_service/items.py` (notamment l.109 et l.169), `borrower_service.py`, `inventory_service.py`, `report_service/loans.py` |
| **Retard** (`due_date < today`) et **calcul de jours de retard** | `circulation_service.py`, `models/circulation.py` (`days_overdue`), `catalog_service/items.py` (l.123-124), `borrower_service.py`, `report_service/loans.py` (l.75, 210) |
| **Vérification d'un prêt actif avant suppression** | `catalog_service/items.py` (`_check_item_has_active_loan`), `catalog_service/records.py` |
| **Réservations lors d'un prêt ou d'un retour** | `circulation_service.py` (interroge directement le modèle `Hold`), `hold_service.py` |

### 1.1 Bugs réels identifiés dans le code source

**Dette 1 — branche historique morte dans `days_overdue`**

Dans `src/bcd_api/models/circulation.py`, `is_overdue` renvoie `False` dès qu'un prêt est rendu. Les tests existants confirment ce contrat : un prêt rendu, même en retard, a `is_overdue is False` et `days_overdue == 0`.

La branche de calcul historique actuellement placée après `if not self.is_overdue` est donc inatteignable et trompeuse, mais elle ne doit pas changer la sémantique publique de la propriété ORM. Le calcul d'un **retour tardif** relève des lectures historiques et doit utiliser `policy.was_returned_late(due_date, return_date)` et `policy.overdue_days(due_date, return_date.date())`.

**Bug 2 — Commits imbriqués : atomicité brisée**

`checkout_items()` (l.243) et `return_items()` (l.351) font chacun un `db.commit()` final. Mais les fonctions de `hold_service` qu'ils appellent committent également en interne :

- `fulfill_hold()` : `db.delete(hold)` → `db.commit()` → puis appelle `_reorder_queue_after_removal()` → second `db.commit()`
- `cancel_hold()` : même structure, deux commits
- `mark_hold_ready()` (appelé par `auto_fill_holds_on_return`) : un seul `db.commit()` ; il ne réordonne pas la file

Un prêt avec réservation produit donc **4 commits successifs** (fulfill + reorder + statut item + commit final circulation). Une erreur réseau ou SQL entre deux commits laisse la base dans un état partiellement persisté et incohérent.

**Bug 3 — Renouvellement : règle documentée absente du code**

La documentation de l'API annonce qu'une réservation active interdit le renouvellement. Dans `renew_items()` le commentaire dit explicitement `# For now, skip hold check as Phase 3 doesn't implement holds`. Cette vérification n'a jamais été implémentée.

**Bug 4 — N+1 massif dans `checkout_items()`**

Dans la boucle de validation (`for item_id_str in item_ids`), chaque exemplaire déclenche :
1. `db.query(Item)` pour charger l'exemplaire
2. `db.query(Hold)` pour chercher la réservation de l'emprunteur courant
3. `db.query(Hold)` pour chercher une réservation `ready` d'un autre emprunteur
4. `db.query(Borrower)` pour résoudre le nom de l'autre emprunteur
5. `db.query(CirculationTransaction)` si l'exemplaire est `on_loan`

Pour 5 livres : jusqu'à 25 requêtes SQL unitaires. Aucun chargement batch.

**Bug 5 — `get_settings` écrit implicitement en transaction métier**

`_get_system_settings` alias `deps.get_settings` crée et committe des réglages par défaut si la ligne `id=1` est absente (`db.add(settings)` → `db.commit()`). Appelée au début de `checkout_items()`, `return_items()` et `renew_items()`, ce commit implicite peut se produire **avant** le commit métier, cassant l'atomicité sans avertissement.

**Bug 6 — `borrowers_to_check` mort dans `return_items()`**

Le set `borrowers_to_check` est construit pendant le retour mais n'est jamais consommé. La documentation du retour mentionne un blocage automatique des emprunteurs en retard — cette logique est absente du code.

### 1.2 Duplications de règles dans les services consommateurs

| Service | Duplication |
|---|---|
| `borrower_service.py` l.748-751 | Limite `loan_limit_teacher` vs `loan_limit_default` selon le rôle |
| `catalog_service/items.py` l.109-124 | Prêt actif + calcul retard ad hoc |
| `catalog_service/items.py` l.163-199 | `_check_item_has_active_loan` : requête prêt actif dupliquée |
| `report_service/loans.py` l.61, 75, 114, 198, 210, 224 | Prédicat `return_date IS NULL`, calcul `(today - due_date).days` |

---

## 2. Décisions architecturales

### 2.1 Pattern retenu

Le domaine suit le pattern **Application Service / Transaction Script + Domain Policy + Unit of Work**, avec une séparation **Command / Query (CQRS léger)** :

- une **commande** charge les données, applique les règles pures, modifie les modèles et possède l'unique transaction ;
- une **policy** est pure : sans SQLAlchemy, sans FastAPI, sans modèles ORM ; reçoit son paramètre `today: date` de façon explicite pour garantir le déterminisme des tests ;
- les **lectures** sont des requêtes SQLAlchemy spécialisées, sans aucun `commit()` ;
- les **services consommateurs** interrogent la DB directement pour leurs lectures complexes et réutilisent les primitives communes (`query_filters`, `policy`).

### 2.2 Structure cible

```text
src/bcd_api/services/
├── circulation_service.py          # façade de compatibilité (phases 1-5), puis imports directs (phase 6)
└── circulation/
    ├── __init__.py
    ├── commands.py                 # checkout_items, return_items, renew_items
    ├── queries.py                  # lectures seules : prêts courants, historiques, prêt actif ciblé
    ├── policy.py                   # règles pures : limites, dates, retards (sans DB, 100% testable)
    ├── query_filters.py            # prédicats SQLAlchemy réutilisables par tous les services
    └── _presentation.py            # formatage partagé : display_title, sérialisation des réponses
```

### 2.3 Contrat transactionnel (Unit of Work)

Chaque commande publique est propriétaire unique de son unité de travail :

```python
try:
    # toutes les lectures, validations et mutations (flush si nécessaire)
    db.flush()
    db.commit()
except Exception:
    db.rollback()
    raise
```

Règles impératives :

- `commands.py` est le **seul** endroit où `commit()` et `rollback()` sont appelés pour un prêt, retour ou renouvellement.
- Aucune fonction appelée depuis une commande ne committe implicitement — y compris `get_settings`.
- Les helpers internes peuvent faire `db.flush()` pour matérialiser des contraintes ou des identifiants, jamais `db.commit()`.

#### Correction de `get_settings` avant toute commande

`main.py` appelle déjà `init_system_settings()` au démarrage et garantit l'existence des réglages par `settings_service.initialize_default_settings(db)`. La Phase 2 doit s'appuyer sur cette initialisation existante :

- transformer `deps.get_settings` en lecture pure, sans `db.add()` ni `db.commit()` ;
- auditer aussi `settings_service.get_settings`, dont le backfill de règles de cote peut encore committer ; aucune commande de circulation ne doit appeler une variante qui écrit ;
- ajouter un test de démarrage et un test de commande confirmant que la lecture des réglages ne crée aucune écriture.

La route FastAPI ne participe pas à l'initialisation : elle reste un wrapper fin.

#### Intégration transactionnelle publique de `hold_service`

Le graphe d'appels complet à réécrire pour supprimer les commits imbriqués :

| Fonction publique actuelle | Commits internes | Fonctions à extraire |
|---|---|---|
| `fulfill_hold()` | 2 (`db.delete` + `_reorder…`) | `fulfill_hold_in_transaction()` |
| `cancel_hold()` | 2 (`db.delete` + `_reorder…`) | `cancel_hold_in_transaction()` |
| `mark_hold_ready()` | 1 | `mark_hold_ready_in_transaction()` |
| `_reorder_queue_after_removal()` | 1 | Devient un helper sans commit |
| `auto_fill_holds_on_return()` | délègue à `mark_hold_ready` | `auto_fill_holds_on_return_in_transaction()` |

Contrat des variantes `_in_transaction` :

```python
# Dans hold_service.py

def fulfill_hold_in_transaction(db: Session, hold_id: int) -> None:
    """Modifie la réservation ; l'appelant possède la transaction. Pas de commit."""
    ...

def fulfill_hold(db: Session, hold_id: int) -> None:
    """Cas autonome (routes /holds). Possède sa propre transaction."""
    try:
        fulfill_hold_in_transaction(db, hold_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
```

Même contrat pour `cancel_hold_in_transaction`, `mark_hold_ready_in_transaction` et `auto_fill_holds_on_return_in_transaction`. `_reorder_queue_after_removal` devient un helper interne sans aucun commit — il est appelé depuis les variantes `_in_transaction`.

### 2.4 Comportement du renouvellement partiel

Le renouvellement est la seule commande à succès partiel autorisé par exemplaire. Le contrat exact est le suivant :

- **Refus métier attendus** (limite de renouvellements atteinte, réservation active, exemplaire non prêté à cet emprunteur) → entrée `failed` dans la réponse ; les autres exemplaires continuent.
- **Erreur technique inattendue** (SQL, contrainte, exception non métier) → `db.rollback()` de toute la commande, exception relancée. L'appel `except Exception as e: failed.append(...)` actuel masque les erreurs techniques — il doit être remplacé.
- **Un seul `db.commit()`** à la fin, après validation de toutes les décisions par exemplaire.

Stratégie : collecter d'abord toutes les décisions (renouvelé / refusé) pour chaque exemplaire, puis appliquer les mutations uniquement pour les succès, puis un seul commit.

### 2.5 Dépendances autorisées

```
circulation.commands  →  hold_service (_in_transaction)
circulation.commands  →  circulation.policy
circulation.commands  →  circulation.query_filters
circulation.commands  →  circulation._presentation
circulation.queries   →  circulation.query_filters
circulation.queries   →  circulation._presentation

borrower_service      →  circulation.policy  (loan_limit_for)
borrower_service      →  circulation.query_filters  (overdue_loan_predicate)
catalog_service       →  circulation.queries  (get_active_loan_for_item)
catalog_service       →  circulation.policy  (is_overdue, overdue_days)
inventory_service     →  circulation.query_filters  (active_loan_predicate)
report_service        →  circulation.query_filters  (overdue_loan_predicate)
report_service        →  circulation.policy  (overdue_days)
```

`circulation` n'importe **jamais** un de ses consommateurs (pas de dépendance circulaire).

### 2.6 Concurrence PostgreSQL — évolution distincte

SQLite utilise actuellement un `QueuePool` à une connexion (`pool_size=1`, `max_overflow=0`). Cette sérialisation locale ne garantit pas la concurrence d'un déploiement PostgreSQL multi-processus. Ce refactoring prépare une évolution PostgreSQL en centralisant les écritures, mais ne la résout pas seul. Une évolution dédiée devra définir :

- les verrous de ligne PostgreSQL (`SELECT ... FOR UPDATE`) sur l'emprunteur et les exemplaires, dans un ordre stable pour éviter les deadlocks ;
- une garantie DB d'au plus un prêt actif par exemplaire (index unique partiel + migration Alembic réversible) ;
- le comportement fonctionnel en cas de conflit concurrent.

Aucun `with_for_update()` ni changement de schéma ne fait partie de la présente portée.

---

## 3. Contrats métier à confirmer avant modification du comportement

| Sujet | État observé dans le code | Décision à valider |
|---|---|---|
| **Renouvellement avec réservation active** | Commentaire `# skip hold check` — jamais implémenté | Confirmer si `waiting` et `ready` bloquent tous deux le renouvellement ; ajouter `RenewalDecision.ACTIVE_HOLD` et réutiliser l'exception structurée existante `ItemHasHoldsException` |
| **`hold_queue_enabled`** | Paramètre existant, non utilisé au retour | Définir si `False` désactive la création, l'interface, et/ou l'auto-promotion ; ne pas modifier sans décision produit |
| **Blocage après retour en retard** | `borrowers_to_check` construit mais jamais consommé | Confirmer si la documentation est erronée ou si c'est une évolution future ; retirer le code mort si non implémenté |
| **Date de renouvellement** | Ajoute `loan_duration_days` à l'ancienne échéance | Conserver ce comportement |
| **Date d'échéance** | Utilise le jour local du prêt | Conserver. La policy reçoit `today: date` explicitement |
| **`get_settings` avec écriture implicite** | Crée et committe les réglages si absents | S'appuyer sur l'initialisation existante au démarrage et rendre les getters appelés par la circulation strictement en lecture seule |

---

## 4. API interne cible

### 4.1 Policy pure (`policy.py`)

```python
@dataclass(frozen=True)
class CirculationPolicy:
    default_loan_limit: int
    teacher_loan_limit: int
    kids_warning_limit: int
    loan_duration_days: int
    renewal_limit: int

    def loan_limit_for(self, role: str) -> int:
        return self.teacher_loan_limit if role in ("teacher", "staff") else self.default_loan_limit

    def checkout_decision(
        self,
        role: str,
        current_loans_count: int,
        additional_count: int,
        is_godot_ui: bool,
    ) -> "CheckoutDecision":
        """Calcule l'avertissement Godot avant la limite stricte."""
        ...

    def checkout_due_date(self, today: date) -> date:
        return today + timedelta(days=self.loan_duration_days)

    def renewed_due_date(self, previous_due_date: date) -> date:
        return previous_due_date + timedelta(days=self.loan_duration_days)

    def renewal_decision(self, renewal_count: int, has_active_hold: bool) -> "RenewalDecision":
        """Distingue ALLOWED, LIMIT_REACHED et ACTIVE_HOLD."""
        ...


# Fonctions pures globales (utilisables sans instance de policy)

def is_overdue(due_date: date, observed_on: date) -> bool:
    return due_date < observed_on

def overdue_days(due_date: date, observed_on: date) -> int:
    """Nombre de jours de retard à une date donnée, 0 si pas en retard."""
    if due_date >= observed_on:
        return 0
    return (observed_on - due_date).days

def was_returned_late(due_date: date, returned_at: datetime) -> bool:
    return returned_at.date() > due_date
```

La policy ne lève aucune exception HTTP. `commands.py` traduit les décisions en exceptions `BCDException`.

`CirculationPolicy.from_settings(settings: SystemSettings) -> CirculationPolicy` est le seul constructeur autorisé depuis l'extérieur.

### 4.2 Prédicats réutilisables (`query_filters.py`)

```python
def active_loan_predicate():
    """Prédicat SQLAlchemy : prêt non rendu."""
    return CirculationTransaction.return_date.is_(None)

def overdue_loan_predicate(today: date):
    """Prédicat SQLAlchemy : prêt non rendu et en retard."""
    return and_(
        CirculationTransaction.return_date.is_(None),
        CirculationTransaction.due_date < today,
    )
```

Ces prédicats remplacent les `CirculationTransaction.return_date.is_(None)` écrits à la main dans 10+ emplacements du codebase.

### 4.3 Primitives de lecture (`queries.py`)

Lecture seule, aucun `commit()` :

```python
def get_active_loan_for_item(db, item_db_id: int) -> Optional[CirculationTransaction]: ...
def get_active_loans_for_items(db, item_db_ids: List[int]) -> List[CirculationTransaction]: ...
def count_active_loans_for_borrower(db, borrower_db_id: int) -> int: ...
def get_borrower_current_loans(db, borrower_id: str) -> List[dict]: ...
def get_item_circulation_history(db, item_id: str, page, page_size, date_from, date_to) -> ItemHistoryResponse: ...
def get_borrower_circulation_history(db, borrower_id: str, page, page_size, date_from, date_to) -> BorrowerHistoryResponse: ...
```

`get_active_loan_for_item` et `get_active_loans_for_items` remplacent `_check_item_has_active_loan` dans `catalog_service` et les requêtes ad hoc de `inventory_service`.

### 4.4 Formatage partagé (`_presentation.py`)

`_display_title(title, shelf_location)` et la sérialisation des champs de retard (construction du dict `is_overdue`, `days_overdue`) sont centralisés ici. Ni `commands.py` ni `queries.py` ne réécrivent ce formatage. Les routes FastAPI n'y accèdent pas directement.

---

## 5. Plan d'exécution incrémental

Chaque phase se termine par une suite de tests verte (`python run_tests.py --fast`).

### Phase 0 — Caractérisation, décisions et tests de robustesse

**But :** verrouiller les comportements complexes et faire valider toutes les ambiguïtés avant toute modification.

1. **Valider les décisions de la section 3** — aucun changement de règle produit ne commence sans cette validation.
2. **Documenter l'initialisation existante des réglages** et écrire les tests garantissant que les getters appelés par la circulation sont strictement en lecture seule.
3. Écrire des tests d'intégration caractérisant les comportements à préserver :
   - Un prêt groupé qui échoue sur un exemplaire déjà prêté annule l'intégralité de l'opération.
   - Un retour groupé contenant un exemplaire non prêté ne retourne aucun des autres exemplaires.
   - Un même `item_id` fourni deux fois dans une commande est rejeté avant toute mutation.
   - Le comportement d'un exemplaire `on_loan` sans transaction active : erreur d'intégrité, réparation ou autre — décision documentée.
   - La décision validée concernant le renouvellement d'un exemplaire réservé.
   - Les calculs de retard et d'échéance : le jour exact de l'échéance (non en retard), le lendemain (en retard), et le calcul historique sur un livre rendu tardivement.

### Phase 1 — Extraction de la policy pure et clarification du modèle ORM

**But :** isoler le moteur de règles métier sans inverser les dépendances `models → services`.

1. Créer `src/bcd_api/services/circulation/policy.py`.
2. Créer `tests/unit/services/test_circulation_policy.py` — couverture 100% de tous les calculs de dates, limites et retards, sans base de données, avec `today` injecté explicitement.
3. Dans `models/circulation.py`, supprimer la branche historique inatteignable de `days_overdue` et documenter que `is_overdue` / `days_overdue` décrivent l'état d'un prêt actif. Le modèle n'importe jamais `services.circulation.policy`.
4. Utiliser `policy.was_returned_late` et `policy.overdue_days` dans les lectures historiques et réponses de retour ; ajouter les tests de non-régression correspondant aux deux sémantiques.
5. Remplacer les recalculs inline de `circulation_service.py` par les fonctions pures.

### Phase 2 — Sécurisation de `get_settings`

**But :** supprimer l'écriture implicite en transaction métier sans épaissir les routes.

1. S'appuyer sur `init_system_settings()` déjà appelé au démarrage dans `main.py`.
2. Transformer `deps.get_settings` en lecture pure (retirer `db.add` + `db.commit`) et vérifier que tout backfill de `settings_service.get_settings` est effectué avant les commandes ou déplacé vers une migration/startup.
3. Ajouter un test de démarrage garantissant la création des réglages, puis vérifier que les tests de la Phase 0 passent toujours.

### Phase 3 — Extraction des lectures (`queries.py` & `query_filters.py`)

**But :** isoler les requêtes de lecture et créer les primitives partagées.

1. Créer `circulation/queries.py` et `circulation/query_filters.py`.
2. Déplacer toutes les fonctions de lecture sans modification logique.
3. Exposer ces fonctions depuis `circulation_service.py` en mode façade de compatibilité.
4. Remplacer dans `catalog_service/items.py` les 4 occurrences de `return_date.is_(None)` et `_check_item_has_active_loan` par `queries.get_active_loan_for_item` et `query_filters.active_loan_predicate`.
5. Remplacer dans `report_service/loans.py` les prédicats et calculs de retard inline par `query_filters.overdue_loan_predicate` et `policy.overdue_days`.
6. Ajouter dans `tests/integration/services/test_circulation_queries.py` un test par fonction de lecture exposée, vérifiant les résultats et l'absence de mutations.

> **Point de vigilance** : cette phase migre les consommateurs. Chaque remplacement doit être couvert par un test de non-régression avant et après, pour détecter tout écart de sémantique.

### Phase 4 — Intégration transactionnelle de `hold_service`

**But :** supprimer les commits imbriqués dans le graphe complet de `hold_service`.

1. Dans `hold_service.py`, rendre `_reorder_queue_after_removal` sans commit (simple accumulation de mutations ORM).
2. Extraire `fulfill_hold_in_transaction`, `cancel_hold_in_transaction`, `mark_hold_ready_in_transaction` et `auto_fill_holds_on_return_in_transaction` sans aucun `db.commit()` ni `db.rollback()`.
3. Réécrire les fonctions publiques autonomes (`fulfill_hold`, `cancel_hold`, `mark_hold_ready`, `auto_fill_holds_on_return`) pour appeler leurs variantes `_in_transaction` puis appliquer leur propre `try / commit / rollback` — le contrat des routes `/holds` est préservé.
4. Vérifier que tous les tests de réservation existants passent.
5. Ajouter un test d'intégration qui force une erreur SQL **après** la mutation de réservation mais **avant** le commit final d'un retour avec réservation, et vérifie qu'aucune mutation n'est persistée (ni retour, ni réordonnancement de queue).

### Phase 5 — Extraction et sécurisation des commandes

**But :** rendre les écritures cohérentes, transactionnelles et sans N+1.

1. Créer `circulation/commands.py`. `commands.py` n'importe pas `queries.py` du même domaine — ses helpers de chargement internes lui sont propres.
2. Déplacer `checkout_items`, `return_items` et `renew_items` en conservant signatures, schémas de réponse, exceptions BCD et codes d'erreur publics.
3. Appliquer un unique `try / commit / except / rollback` par commande :
   - **prêt** : tout ou rien — un seul commit à la fin, après validation complète de tous les exemplaires.
   - **retour** : tout ou rien.
   - **renouvellement** : collecter toutes les décisions (renouvelé / refusé) pour tous les exemplaires, appliquer les mutations des succès uniquement, un seul commit. Remplacer `except Exception as e: failed.append(...)` par une capture des seules exceptions métier attendues — les erreurs techniques relancent avec rollback global.
4. Charger exemplaires, prêts actifs et réservations en batch avant toute mutation dans `checkout_items` : une requête `IN` pour les exemplaires, une pour les prêts actifs, une pour les réservations. Valider toutes les entrées avant la première mutation.
5. Appeler exclusivement les variantes `_in_transaction` de `hold_service`, jamais les fonctions publiques.
6. Implémenter `renewal_decision` dans `policy.py` avec la vérification de réservation active (décision de la Phase 0) et utiliser `ItemHasHoldsException` pour le refus structuré correspondant.
7. Supprimer le code mort lié à `borrowers_to_check` (Phase 0 aura documenté la décision).
8. Ajouter dans `tests/integration/services/test_circulation_commands.py` :
   - Atomicité du prêt (tout ou rien sur un lot mixte).
   - Atomicité du retour (tout ou rien).
   - Renouvellement : succès partiel métier vs rollback complet sur erreur technique.
   - Nombre de requêtes SQL borné pour un prêt de 5 exemplaires, via un compteur d'événements SQLAlchemy de test — pas un nombre fragile, une borne maximale.

### Phase 6 — Alignement des services consommateurs restants

**But :** finaliser la migration des duplications dans `borrower_service` et `inventory_service`.

1. Dans `borrower_service.py` : utiliser `CirculationPolicy.from_settings(settings).loan_limit_for(role)` pour l'enrichissement ; utiliser `query_filters.overdue_loan_predicate` pour les filtres d'emprunteurs.
2. Dans `inventory_service.py` : utiliser `query_filters.active_loan_predicate()` dans les guards de suppression d'exemplaires.
3. Ajouter ou renforcer des tests de caractérisation ciblés pour chaque migration de consommateur ; ils doivent passer avant et après le déplacement afin de démontrer l'absence de régression.

### Phase 7 — Nettoyage de la façade et validation finale

**But :** finaliser le refactoring et valider la cohérence globale.

1. Remplacer le contenu de `circulation_service.py` par des imports directs :
   ```python
   from .circulation.commands import checkout_items, return_items, renew_items
   from .circulation.queries import (
       get_borrower_current_loans,
       get_borrower_circulation_history,
       get_item_circulation_history,
   )
   ```
2. Mettre à jour les imports dans `api/v1/` qui pointent directement sur `circulation_service`.
3. Lancer `python run_tests.py` (suite complète) et corriger tous les imports obsolètes.
4. Vérifier les critères d'acceptation de la section 7.

---

## 6. Intégrations ouvertes par ce refactoring

Ces évolutions ne font pas partie de la présente portée mais sont rendues possibles ou significativement simplifiées par ce refactoring.

### 6.1 Enrichissement de l'API emprunteur

Avec `CirculationPolicy` disponible en dehors de `circulation_service`, `borrower_service.enrich_borrower` peut exposer `renewals_remaining` par prêt actif, ou un `checkout_capacity` précalculé. Le client Godot calcule aujourd'hui l'avertissement de limite côté serveur dans `checkout_items`, ce qui oblige un aller-retour complet pour afficher un avertissement. Un endpoint dédié `/borrowers/{id}/capacity` deviendrait trivial à implémenter.

### 6.2 Vérification des réservations dans `create_hold`

`hold_service.create_hold()` reçoit une notice bibliographique, non un exemplaire. Une évolution future peut vérifier si l'emprunteur possède déjà un prêt actif sur **un exemplaire de cette notice**, via une primitive dédiée du type `get_active_loans_for_borrower_and_record()` ; `get_active_loan_for_item()` ne convient pas à ce cas.

### 6.3 Job de réconciliation statut/transaction

`inventory_service` travaille sur le statut dénormalisé (`item.status`). Avec `query_filters.active_loan_predicate()`, un job de réconciliation peut détecter :
- les exemplaires `on_loan` sans transaction active (incohérence de statut) ;
- les exemplaires `available` avec une transaction active (incohérence inverse).

Ce job peut être exposé comme route d'administration ou lancé au démarrage.

### 6.4 Cache applicatif des réglages

Évolution distincte : un éventuel cache doit stocker un snapshot de valeurs scalaires, disposer d'un TTL réel et être invalidé lors de `update_settings`. Il ne doit ni utiliser `@lru_cache` comme faux TTL, ni conserver une instance ORM liée à une session.

### 6.5 Métriques harmonisées dans `report_service`

Avec `policy.overdue_days` et `was_returned_late` disponibles et testées, `report_service` peut harmoniser ses métriques avec la sémantique de circulation commune, par exemple :
- **taux de renouvellement par classe** (croisement avec `class_service`) ;
- **durée réelle de prêt vs durée prévue** (exploitable avec l'historique paginé de `queries.py`).

Les rapports actuels calculent déjà leurs retards ; cette évolution vise à éviter des divergences futures, non à débloquer des métriques impossibles.

---

## 7. Stratégie de tests

### Tests unitaires — Sans base de données
Fichier : `tests/unit/services/test_circulation_policy.py`.  
Couvre exhaustivement : calcul de limites (étudiant vs prof/staff), avertissements Godot, calcul d'échéances et de renouvellement, calcul déterministe des jours de retard, `was_returned_late`, comportement de `RenewalDecision` (ALLOWED / LIMIT_REACHED / ACTIVE_HOLD). **Couverture cible : 100%.**

### Tests d'intégration — Avec base de données
- `tests/integration/services/test_circulation_commands.py` : atomicité du prêt et du retour (tout ou rien), succès partiel métier du renouvellement vs rollback sur erreur technique, prêt avec réservation (aucune mutation si erreur avant commit final), exemplaires dupliqués dans la même commande, états incohérents.
- `tests/integration/services/test_circulation_queries.py` : résultats corrects par fonction de lecture, absence de mutations.
- Tests de non-régression par consommateur migré (Phases 3 et 6).

### Règle sur les tests de performance
Pour le prêt multiple : vérifier qu'un prêt de N exemplaires produit un nombre de requêtes SQL borné par une constante (pas proportionnel à N). Ne pas imposer un nombre exact fragile dépendant du dialecte SQL ou du chargement ORM.

---

## 8. Critères d'acceptation globaux

Le refactoring est considéré terminé si :

1. Chaque commande possède une transaction explicite `try / commit / except / rollback` unique ; prêt et retour sont tout-ou-rien ; le renouvellement ne produit des succès partiels que pour les refus métier attendus, et rollbacke entièrement sur erreur technique.
2. Aucune fonction appelée depuis une commande de circulation ne fait de `commit()` ou `rollback()` implicite — y compris `get_settings`.
3. Toutes les règles de calcul de limites, d'échéances et de retards sont centralisées dans `policy.py` et testées à 100% sans base de données.
4. La sémantique est explicite et testée : `CirculationTransaction.days_overdue` décrit un prêt actif et vaut zéro après retour ; les retards historiques utilisent `policy.was_returned_late` et `policy.overdue_days`.
5. Les commandes de prêt ne souffrent plus du problème N+1 : le nombre de requêtes SQL est borné indépendamment de la taille du lot.
6. Les demandes contenant des exemplaires dupliqués ou des états incohérents ont un comportement déterministe, documenté et testé avant toute mutation.
7. Les services consommateurs (`borrower_service`, `catalog_service`, `report_service`, `inventory_service`) utilisent les primitives communes de `query_filters` et `policy` ; aucune duplication de règle de calcul de retard ou de limite n'est introduite.
8. La façade `circulation_service.py` est entièrement remplacée par des imports directs à la fin de la Phase 7 ; aucun import obsolète ne subsiste dans `api/v1/`.
9. `python run_tests.py --fast` puis `python run_tests.py` passent au vert sans aucune erreur.
10. Couverture globale des nouveaux modules : **≥ 80%** ; couverture de `policy.py` : **100%** ; couverture des chemins transactionnels d'intégrité dans `commands.py` : **100%**.
