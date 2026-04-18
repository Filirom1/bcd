# CLI Quickstart Guide: BCD Library System

**Feature**: School Library Management System (BCD)
**Date**: 2026-01-30
**Version**: 1.0.0

## Overview

This guide provides a complete reference for the BCD command-line interface. The CLI is designed for librarians to manage daily library operations including circulation, cataloging, and borrower management.

**Key Features**:
- Interactive barcode scanner mode for checkout/return
- BNF API integration for ISBN-based cataloging
- Batch operations via CSV import
- Report generation (overdue, statistics)
- Bilingual interface (French/English)

---

## Installation & Setup

### Starting the API Server

The CLI communicates with a local REST API server. Start the server first:

```bash
# Development mode (localhost only)
bcd-api serve --port 8000

# Production mode (accessible on network)
bcd-api serve --host 0.0.0.0 --port 8000
```

**Server Status**:
```bash
# Check if server is running
curl http://localhost:8000/api/v1/admin/settings

# Expected: JSON response with system settings
```

### CLI Configuration

Configure the CLI to connect to the API:

```bash
# Set API URL (default: http://localhost:8000)
bcd config --api-url http://localhost:8000

# Set language (fr or en)
bcd config --language fr

# View current configuration
bcd config --show
```

**Configuration File**: `~/.bcd/config.json`

```json
{
  "api_url": "http://localhost:8000",
  "language": "fr",
  "timeout": 30
}
```

---

## Command Structure

All commands follow this pattern:

```
bcd <command> <subcommand> [arguments] [options]
```

**Command Groups**:
- `checkout`, `return`, `renew` - Circulation operations
- `catalog` - Bibliographic records and items
- `borrower` - Borrower management
- `item` - Item status and history
- `hold` - Reservations (librarian-mediated)
- `report` - Statistics and reports
- `admin` - System administration
- `config` - CLI configuration

---

## Circulation Operations

### Checkout (Interactive Mode)

**Interactive barcode scanner workflow** - Most common usage:

```bash
bcd checkout
```

**Example Session**:
```
📖 BCD Library - Prêt / Checkout
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scannez l'ID de l'emprunteur / Scan borrower ID:
> 101                                    ← Barcode scanner input

✓ Emprunteur / Borrower: Amira BENALI (CP-A)
  Prêts en cours / Current loans: 0/2
  Statut / Status: Actif / Active

Scannez le code-barres du document (Entrée pour terminer)
Scan item barcode (Enter to finish):
> 785                                    ← Scanner input

✓ Ajouté / Added: Ils ont arrêté mon père
  Auteur / Author: Carmi, Danielle
  Cote / Call #: 800.000

Scan item barcode (Enter to finish):
> 787                                    ← Scanner input

✓ Ajouté / Added: Stuart Little
  Auteur / Author: White, E.B.
  Cote / Call #: 813.000

Scan item barcode (Enter to finish):
> [Enter]                                ← Done scanning

Résumé du prêt / Checkout Summary:
┌─────────┬──────────────────────────┬──────────────┐
│ Item ID │ Titre / Title            │ Date retour  │
│         │                          │ Due Date     │
├─────────┼──────────────────────────┼──────────────┤
│ 785     │ Ils ont arrêté mon père  │ 13/02/2026   │
│ 787     │ Stuart Little            │ 13/02/2026   │
└─────────┴──────────────────────────┴──────────────┘

Confirmer le prêt ? / Confirm checkout? [O/n]: O

✅ 2 documents prêtés à Amira BENALI
   2 items checked out to Amira BENALI
```

### Checkout (Direct Mode)

**For scripting or when barcode scanner unavailable**:

```bash
# Checkout one item
bcd checkout 101 785

# Checkout multiple items
bcd checkout 101 785 787 790

# With explicit IDs
bcd checkout --borrower-id 101 --item-ids 785,787
```

**Output**:
```
✅ 2 documents prêtés / items checked out
   Emprunteur / Borrower: Amira BENALI (CP-A)
   Date de retour / Due date: 13/02/2026

┌─────────┬──────────────────────────┐
│ Item ID │ Titre / Title            │
├─────────┼──────────────────────────┤
│ 785     │ Ils ont arrêté mon père  │
│ 787     │ Stuart Little            │
└─────────┴──────────────────────────┘
```

**Error Handling**:
```bash
bcd checkout 101 999

# Output:
❌ Erreur / Error: Document non trouvé / Item not found
   Item ID: 999
```

---

### Return (Interactive Mode)

```bash
bcd return
```

**Example Session**:
```
📖 BCD Library - Retour / Return
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scannez le code-barres du document (Entrée pour terminer)
Scan item barcode (Enter to finish):
> 785

✓ Document / Item: Ils ont arrêté mon père (ID: 785)
  Emprunteur / Borrower: Amira BENALI (CP-A)
  Prêté le / Checked out: 30/01/2026
  Dû le / Due: 13/02/2026
  ✓ À temps / On time

Scan item barcode (Enter to finish):
> 787

✓ Document / Item: Stuart Little (ID: 787)
  Emprunteur / Borrower: Amira BENALI (CP-A)
  Prêté le / Checked out: 30/01/2026
  Dû le / Due: 13/02/2026
  ⚠️ En retard de 3 jours / 3 days overdue

Scan item barcode (Enter to finish):
> [Enter]

Résumé du retour / Return Summary:
┌─────────┬──────────────────────────┬─────────────┬──────────┐
│ Item ID │ Titre / Title            │ Emprunteur  │ Statut   │
│         │                          │ Borrower    │ Status   │
├─────────┼──────────────────────────┼─────────────┼──────────┤
│ 785     │ Ils ont arrêté mon père  │ BENALI A.   │ ✓        │
│ 787     │ Stuart Little            │ BENALI A.   │ ⚠️ +3j   │
└─────────┴──────────────────────────┴─────────────┴──────────┘

Confirmer le retour ? / Confirm return? [O/n]: O

✅ 2 documents retournés / items returned
   ⚠️ 1 document en retard / overdue item
   → L'emprunteur a été bloqué / Borrower has been blocked
```

### Return (Direct Mode)

```bash
# Return one or more items
bcd return 785 787 790
```

---

### Renew

**Interactive renewal** - Shows items, allows selection:

```bash
bcd renew 101
```

**Example Session**:
```
📖 BCD Library - Renouvellement / Renewal
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Emprunteur / Borrower: Amira BENALI (CP-A)
Prêts en cours / Current loans: 2

┌───┬─────────┬──────────────────────────┬──────────┬────────────┬─────────────┐
│ # │ Item ID │ Titre / Title            │ Dû le    │ Renouv.    │ Peut        │
│   │         │                          │ Due      │ Renewals   │ Can Renew?  │
├───┼─────────┼──────────────────────────┼──────────┼────────────┼─────────────┤
│ 1 │ 785     │ Ils ont arrêté mon père  │ 13/02/26 │ 0/2        │ ✓ Oui       │
│ 2 │ 787     │ Stuart Little            │ 13/02/26 │ 0/2        │ ✗ Réservé   │
└───┴─────────┴──────────────────────────┴──────────┴────────────┴─────────────┘

Sélectionner les documents à renouveler (ex: 1,2) / Select items (e.g., 1,2):
> 1

Nouvelle date de retour / New due date: 27/02/2026

Confirmer le renouvellement ? / Confirm renewal? [O/n]: O

✅ 1 document renouvelé / item renewed
❌ 1 document non renouvelé / item not renewed
   → Item 787: Réservation en attente / Hold pending
```

**Direct Renewal** (renew all eligible items):
```bash
bcd renew 101 --all
```

---

## Cataloging Operations

### Add Bibliographic Record (ISBN Lookup)

**Automatic BNF API lookup** - Fastest method:

```bash
bcd catalog add --isbn 978-2-8006-8734-6
```

**Example Session**:
```
📖 BCD - Catalogage / Cataloging
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 Recherche BNF pour ISBN: 978-2-8006-8734-6
   Searching BNF for ISBN: 978-2-8006-8734-6

✓ Trouvé / Found in BNF catalog:

Titre / Title: L'équipe des mascrottes
Auteur / Author: Petit, Dominique
Illustrateur / Illustrator: Rouzé, Marina
Éditeur / Publisher: Hemma
Année / Year: 2004
Collection / Series: La mini C (24)
Langue / Language: Français (fre)
Pages: 83
Public / Audience: Enfant / Child
Illustrations: Oui / Yes

Valider ces informations ? / Accept this data? [O/n]: O

✓ Notice bibliographique créée / Bibliographic record created
  ID: 1

Créer un exemplaire ? / Create item copy? [O/n]: O

Numéro d'inventaire / Item ID: 785
Cote / Call number [800.000]: 800.000
Emplacement / Shelf location: Fiction - Section A

✅ Notice et exemplaire créés / Record and item created
   Notice ID: 1
   Exemplaire ID / Item ID: 785
```

**Override Fields**:
```bash
# Override specific fields from BNF data
bcd catalog add --isbn 978-2-8006-8734-6 \
  --category "Lire des histoires" \
  --genre "Album" \
  --level "CP-CE1"
```

---

### Add Bibliographic Record (Manual Entry)

**When ISBN not available or not found**:

```bash
bcd catalog add --manual
```

**Example Session (Interactive Form)**:
```
📖 Entrée manuelle / Manual Entry
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Titre / Title *: Les trois petits cochons
Sous-titre / Subtitle [optionnel]:
Auteur(s) / Author(s): Perrault, Charles
Illustrateur(s) / Illustrator(s): Dupont, Marie
Éditeur / Publisher: Flammarion
Année / Year: 2020
ISBN [optionnel]:
Collection / Series: Contes classiques
Numéro / Volume: 3
Support / Medium [Livre]: Livre
Langue / Language [fre]: fre
Public / Audience (child/youth/adult) [child]: child
Catégorie / Category: Contes
Genre: Album
Niveau / Level: Maternelle
Nombre de pages / Page count: 32
Illustrations (O/n) [O]: O
Résumé / Summary:
> L'histoire des trois petits cochons qui...

✓ Notice bibliographique créée / Bibliographic record created
  ID: 2
```

---

### Search Catalog

```bash
# Search by title
bcd catalog search --title "petit cochon"

# Search by author
bcd catalog search --author "Perrault"

# Search by ISBN
bcd catalog search --isbn 978-2-8006-8734-6

# Search by call number (Cote)
bcd catalog search --call-number "800.000"

# Combined search
bcd catalog search --q "Harry Potter"

# Filter by language and audience
bcd catalog search --q "histoire" --language fre --audience child
```

**Output**:
```
🔍 Résultats de recherche / Search Results (3 trouvés / found)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Ils ont arrêté mon père
   Auteur: Carmi, Danielle
   Année: 2004 | ISBN: 978-2-8006-8734-6
   Cote: 800.000 | Exemplaires: 2 (1 disponible)

2. Les trois petits cochons
   Auteur: Perrault, Charles
   Année: 2020 | Collection: Contes classiques (3)
   Cote: 398.200 | Exemplaires: 1 (disponible)

3. Stuart Little
   Auteur: White, E.B.
   Année: 1945 | ISBN: 978-0-06-026395-7
   Cote: 813.000 | Exemplaires: 1 (en prêt)
```

---

### Import Catalog (CSV)

```bash
# Import bibliographic records and items
bcd catalog import /path/to/bibliographic.csv

# With validation only (dry run)
bcd catalog import /path/to/bibliographic.csv --dry-run
```

**CSV Format** (21 fields):
```csv
Inventaire;Cote;Rubrique;Genre;Titre;SousTitre;ISBN;Auteur;Illustrateur;Annee;Editeur;Collection;Numero;Support;Mots-clefs;Niveau;Description;Taille;Date achat;Financement;Empruntable
785;800.000;Lire des histoires;Album;Ils ont arrêté mon père;;978-2-8006-8734-6;Carmi (Danielle);;2004;Flammarion;;;Livre;famille;CP-CE1;Un récit...;128p;2024-09-15;Budget 2024;Oui
```

**Output**:
```
📥 Import en cours / Importing...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Lignes traitées / Rows processed: 100
✓ Notices créées / Records created: 45
✓ Exemplaires créés / Items created: 100
⚠️ Doublons ignorés / Duplicates skipped: 2
❌ Erreurs / Errors: 1

Erreurs détaillées / Error details:
  Ligne 42 / Row 42: ISBN invalide / Invalid ISBN: "123-456"

✅ Import terminé / Import complete
   45 notices, 100 exemplaires / 45 records, 100 items
```

---

## Borrower Management

### Add Borrower

```bash
# Interactive mode
bcd borrower add

# Direct mode
bcd borrower add --borrower-id 101 --name "Amira BENALI" --class "CP-A"

# With all options
bcd borrower add \
  --borrower-id 125 \
  --first-name "Sophie" \
  --last-name "MARTIN" \
  --class "CE1-B" \
  --role student
```

**Example (Interactive)**:
```
👤 Nouvel emprunteur / New Borrower
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Numéro d'emprunteur / Borrower ID *: 126
Prénom / First name *: Lucas
Nom / Last name *: DUBOIS
Rôle / Role (student/teacher/staff) [student]: student
Classe / Class: CP-A

✓ Emprunteur créé / Borrower created
  ID: 126
  Code-barres / Barcode: BOR126 (généré / generated)
```

---

### List Borrowers

```bash
# List all borrowers
bcd borrower list

# Filter by class
bcd borrower list --class "CP-A"

# Filter by role
bcd borrower list --role student

# Show only active borrowers
bcd borrower list --active

# Show only blocked borrowers
bcd borrower list --blocked
```

**Output**:
```
👥 Emprunteurs / Borrowers (24 trouvés / found)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Classe / Class: CP-A
┌──────────┬──────────────────────┬────────┬──────────────────────┐
│ ID       │ Nom / Name           │ Prêts  │ Statut / Status      │
│          │                      │ Loans  │                      │
├──────────┼──────────────────────┼────────┼──────────────────────┤
│ 101      │ BENALI Amira         │ 2/2    │ ✓ Actif              │
│ 102      │ DUBOIS Lucas         │ 0/2    │ ✓ Actif              │
│ 103      │ MARTIN Léa           │ 1/2    │ ⚠️ Bloqué (en retard)│
└──────────┴──────────────────────┴────────┴──────────────────────┘
```

---

### View Borrower Details

```bash
# Show current loans
bcd borrower current 101

# Show full history
bcd borrower history 101

# Combined view
bcd borrower show 101
```

**Output (Current Loans)**:
```
👤 Amira BENALI (ID: 101)
   Classe / Class: CP-A
   Statut / Status: ✓ Actif / Active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📚 Prêts en cours / Current Loans: 2/2

┌─────────┬──────────────────────────┬─────────────┬─────────┐
│ Item ID │ Titre / Title            │ Dû le / Due │ Statut  │
├─────────┼──────────────────────────┼─────────────┼─────────┤
│ 785     │ Ils ont arrêté mon père  │ 13/02/2026  │ ✓       │
│ 787     │ Stuart Little            │ 13/02/2026  │ ✓       │
└─────────┴──────────────────────────┴─────────────┴─────────┘

📊 Statistiques / Statistics:
   Total emprunts / checkouts: 15
   En retard / Overdue: 0
```

---

### Import Borrowers (CSV)

```bash
bcd borrower import /path/to/students.csv
```

**CSV Format**:
```csv
StudentID,FirstName,LastName,Class,BlockReason
101,Amira,BENALI,CP-A,
102,Lucas,DUBOIS,CP-A,
103,Léa,MARTIN,CP-A,Livre perdu
```

**Output**:
```
📥 Import d'emprunteurs / Importing Borrowers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Lignes traitées / Rows processed: 217
✓ Emprunteurs créés / Borrowers created: 215
⚠️ Doublons ignorés / Duplicates skipped: 2

✅ Import terminé / Import complete
```

---

## Item Operations

### View Item Status

```bash
bcd item status 785
```

**Output**:
```
📖 Exemplaire / Item: 785
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Titre / Title: Ils ont arrêté mon père
Auteur / Author: Carmi, Danielle
Cote / Call #: 800.000
Emplacement / Location: Fiction - Section A - Row 3

Statut / Status: 🔴 En prêt / On loan
  Emprunteur / Borrower: Amira BENALI (CP-A)
  Prêté le / Checked out: 30/01/2026
  Dû le / Due: 13/02/2026

État / Condition: Bon / Good
Empruntable / Loanable: Oui / Yes
```

---

### View Item History

```bash
bcd item history 785
```

**Output**:
```
📖 Historique de circulation / Circulation History
   Item 785: Ils ont arrêté mon père
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 Prêt en cours / Current Loan:
   Emprunteur: BENALI Amira (CP-A)
   Depuis / Since: 30/01/2026
   Retour prévu / Due: 13/02/2026

📜 Historique / History (5 derniers prêts / last 5 loans):

┌──────────────┬──────────────────┬──────────────┬──────────────┐
│ Emprunteur   │ Prêt / Checkout  │ Retour       │ Retard       │
│ Borrower     │                  │ Return       │ Late         │
├──────────────┼──────────────────┼──────────────┼──────────────┤
│ BENALI A.    │ 30/01/2026       │ (en cours)   │ -            │
│ DUBOIS L.    │ 15/01/2026       │ 25/01/2026   │ -            │
│ MARTIN L.    │ 05/01/2026       │ 20/01/2026   │ +1 jour      │
│ PETIT A.     │ 10/12/2025       │ 22/12/2025   │ -            │
│ BENALI A.    │ 25/11/2025       │ 08/12/2025   │ -            │
└──────────────┴──────────────────┴──────────────┴──────────────┘

📊 Statistiques:
   Total prêts / Circulations: 7
   Taux de retard / Late rate: 14%
```

---

## Hold/Reservation Management

### Place Hold (Librarian-Mediated)

```bash
# Interactive
bcd hold add

# Direct
bcd hold add 105 --biblio-id 1
```

**Example (Interactive)**:
```
📌 Nouvelle réservation / New Hold
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ID emprunteur / Borrower ID: 105
ID notice / Bibliographic ID: 1

✓ Notice / Record: Ils ont arrêté mon père
  Exemplaires / Copies: 2 (0 disponibles / available)
  Réservations / Holds: 1 en attente / waiting

✓ Emprunteur / Borrower: Emma BERNARD (CP-A)

Créer la réservation ? / Create hold? [O/n]: O

✅ Réservation créée / Hold created
   Position dans la file / Queue position: 2
   Disponibilité estimée / Estimated availability: ~7 jours / days
```

---

### View Holds for Title

```bash
bcd hold list-for-title 1
```

**Output**:
```
📌 Réservations / Holds for: Ils ont arrêté mon père
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────┬──────────────────┬─────────────┬────────────────┐
│ Pos. │ Emprunteur       │ Classe      │ Date réserv.   │
│      │ Borrower         │ Class       │ Hold date      │
├──────┼──────────────────┼─────────────┼────────────────┤
│ 1    │ PETIT Adam       │ CP-A        │ 28/01/2026     │
│ 2    │ BERNARD Emma     │ CP-A        │ 30/01/2026     │
└──────┴──────────────────┴─────────────┴────────────────┘
```

---

### View Ready for Pickup

```bash
bcd hold ready
```

**Output**:
```
📦 Réservations prêtes / Holds Ready for Pickup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────┬─────────────┬──────────────────────┬─────────────┐
│ Emprunteur       │ Classe      │ Titre                │ Expire dans │
│ Borrower         │ Class       │ Title                │ Expires in  │
├──────────────────┼─────────────┼──────────────────────┼─────────────┤
│ PETIT Adam       │ CP-A        │ Ils ont arrêté...    │ 2 jours     │
│ MARTIN Sophie    │ CE1-B       │ Harry Potter...      │ 1 jour      │
└──────────────────┴─────────────┴──────────────────────┴─────────────┘

💡 Tip: Notifiez les emprunteurs / Notify borrowers
```

---

## Reports

### Overdue Report

```bash
# All classes
bcd report overdue

# Specific class
bcd report overdue --class "CP-A"

# PDF format (for printing)
bcd report overdue --format pdf --output overdue_report.pdf
```

**Output (JSON format)**:
```
📊 Rapport des retards / Overdue Report
   Généré le / Generated: 30/01/2026 15:30
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Classe / Class: CP-A (3 retards / overdue)
┌─────────────────┬─────────┬──────────────────────┬──────────┬─────────┐
│ Emprunteur      │ Item ID │ Titre / Title        │ Dû le    │ Retard  │
│ Borrower        │         │                      │ Due      │ Days    │
├─────────────────┼─────────┼──────────────────────┼──────────┼─────────┤
│ MARTIN Léa      │ 790     │ Le Petit Prince      │ 20/01/26 │ +10j    │
│ DUBOIS Lucas    │ 792     │ Charlotte's Web      │ 25/01/26 │ +5j     │
│ PETIT Adam      │ 788     │ Matilda              │ 28/01/26 │ +2j     │
└─────────────────┴─────────┴──────────────────────┴──────────┴─────────┘

Classe / Class: CE1-A (1 retard / overdue)
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 12 documents en retard / overdue items
```

**PDF Output**: One page per class, ready for distribution.

---

### Never Borrowed Report

```bash
bcd report never-borrowed

# Limit results
bcd report never-borrowed --limit 20
```

**Output**:
```
📊 Documents jamais empruntés / Never Borrowed
   Année scolaire / Academic year: 2025-2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────┬────────────────────────────┬─────────────────┬──────┐
│ ID  │ Titre / Title              │ Auteur          │ Année│
├─────┼────────────────────────────┼─────────────────┼──────┤
│ 42  │ Mathématiques CE2          │ Dupont, Marie   │ 2020 │
│ 58  │ Grammaire avancée          │ Martin, Paul    │ 2019 │
│ 91  │ Histoire de France         │ Bernard, Jean   │ 2021 │
└─────┴────────────────────────────┴─────────────────┴──────┘

Total: 15 notices / records (3% de la collection / of collection)
```

---

### Most Borrowed Report

```bash
# Top 20 titles this year
bcd report most-borrowed

# Top 50 of all time
bcd report most-borrowed --limit 50 --period all-time

# This month
bcd report most-borrowed --period month
```

**Output**:
```
📊 Titres les plus empruntés / Most Borrowed Titles
   Période / Period: Année scolaire 2025-2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────┬────────────────────────────┬─────────────────┬──────────┐
│ Rang │ Titre / Title              │ Auteur          │ Prêts    │
│ Rank │                            │ Author          │ Checkouts│
├──────┼────────────────────────────┼─────────────────┼──────────┤
│ 1    │ Harry Potter (tome 1)      │ Rowling, J.K.   │ 42       │
│ 2    │ Le Petit Prince            │ Saint-Exupéry   │ 38       │
│ 3    │ Charlotte's Web            │ White, E.B.     │ 35       │
│ 4    │ Matilda                    │ Dahl, Roald     │ 32       │
│ 5    │ Les trois petits cochons   │ Perrault        │ 28       │
└──────┴────────────────────────────┴─────────────────┴──────────┘
```

---

## Administration

### View/Update Settings

```bash
# View current settings
bcd admin settings

# Update specific setting
bcd admin settings --set loan_limit_default=3
bcd admin settings --set loan_duration_days=21
bcd admin settings --set language=en

# Multiple settings
bcd admin settings \
  --set loan_limit_default=3 \
  --set loan_duration_days=21 \
  --set barcode_type=code128
```

**Output**:
```
⚙️ Paramètres système / System Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Format des IDs / ID Format: numeric
Regex de validation / Validation: ^\d+$
Type de code-barres / Barcode: code39

Limite de prêt / Loan limit: 2 (élèves / students)
Limite de prêt / Loan limit: 5 (enseignants / teachers)
Durée de prêt / Loan duration: 14 jours / days
Renouvellements max / Max renewals: 2

Expiration réservation / Hold expiry: 3 jours / days

Langue / Language: fr
Année scolaire / Academic year: 2025-2026
Nom bibliothèque / Library: BCD École Primaire
```

---

### Backup Database

```bash
# SQLite backup (default)
bcd admin backup --output bcd_backup_$(date +%Y%m%d).db

# SQL dump
bcd admin backup --format sql --output bcd_backup.sql
```

**Output**:
```
💾 Sauvegarde / Backup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Base de données sauvegardée / Database backed up
  Fichier / File: bcd_backup_20260130.db
  Taille / Size: 2.4 MB

  Contenu / Contents:
    - 500 emprunteurs / borrowers
    - 5,247 notices bibliographiques / bibliographic records
    - 8,532 exemplaires / items
    - 18,234 transactions de prêt / circulation transactions
```

---

### Generate Barcodes

```bash
# Generate borrower barcodes
bcd admin barcode-generate --borrowers 101,102,103 --output borrower_barcodes.pdf

# Generate item barcodes
bcd admin barcode-generate --items 785,787,790 --output item_barcodes.pdf

# All borrowers in a class
bcd admin barcode-generate --class "CP-A" --output cp_a_barcodes.pdf
```

**Output**:
```
🏷️ Génération de codes-barres / Generating Barcodes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Codes-barres générés / Barcodes generated: 24
  Type: Code 39
  Format: Avery 5160 (30 étiquettes / labels par page)

💾 Fichier / File: cp_a_barcodes.pdf (2 pages)

💡 Tip: Imprimez sur du papier d'étiquettes Avery 5160
        Print on Avery 5160 label sheets
```

---

## Tips & Tricks

### Keyboard Shortcuts

When in interactive mode:
- `Ctrl+C` - Cancel current operation
- `Ctrl+D` or `Enter` (empty) - Finish scanning items
- `Ctrl+Z` - Undo last scan (before confirmation)

### Barcode Scanner Configuration

Most barcode scanners work as keyboard devices and send an `Enter` after each scan. No special configuration needed.

**If scanner not working**:
1. Check USB connection
2. Test scanner in text editor (should type barcode + Enter)
3. Try manual entry mode: `bcd checkout --manual`

### Performance Tips

**Large imports**:
```bash
# Import in smaller batches
split -l 100 large_file.csv batch_
for file in batch_*; do
  bcd catalog import "$file"
done
```

**Slow searches**:
```bash
# Use specific field searches instead of general query
bcd catalog search --isbn "978-2-8006-8734-6"  # Fast
bcd catalog search --q "mascrottes"             # Slower (full-text)
```

---

## Troubleshooting

### API Connection Errors

```
❌ Erreur: Cannot connect to BCD API server
```

**Solution**:
```bash
# 1. Check if server is running
curl http://localhost:8000/api/v1/admin/settings

# 2. Start server if not running
bcd-api serve --port 8000

# 3. Check CLI configuration
bcd config --show
```

---

### Blocked Borrower

```
❌ Emprunteur bloqué / Borrower blocked
   Raison / Reason: Documents en retard / Overdue items
```

**Solution**:
```bash
# 1. Check current loans
bcd borrower current 103

# 2. Return overdue items
bcd return 790 792

# 3. Manually unblock if needed
bcd borrower unblock 103
```

---

### Duplicate ISBN

```
❌ ISBN already exists in catalog
   Notice ID: 42
```

**Solution**:
```bash
# Add another copy (item) instead
bcd catalog add-item --biblio-id 42 --item-id 999
```

---

## Quick Reference Card

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                    BCD CLI - Quick Reference
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CIRCULATION
  bcd checkout                 Interactive checkout (scan IDs)
  bcd return                   Interactive return (scan items)
  bcd renew <borrower-id>      Renew items (select which ones)

CATALOGING
  bcd catalog add --isbn <isbn>     Add via BNF lookup
  bcd catalog add --manual          Manual entry
  bcd catalog search --q <query>    Search catalog
  bcd catalog import <file.csv>     Bulk import

BORROWERS
  bcd borrower add                  Add new borrower
  bcd borrower list --class <name>  List by class
  bcd borrower current <id>         Current loans
  bcd borrower import <file.csv>    Bulk import

ITEMS
  bcd item status <item-id>         Item details
  bcd item history <item-id>        Circulation history

HOLDS
  bcd hold add <borrower> <biblio>  Place reservation
  bcd hold ready                    Ready for pickup

REPORTS
  bcd report overdue [--class]      Overdue items
  bcd report never-borrowed         Unused titles
  bcd report most-borrowed          Popular titles

ADMIN
  bcd admin settings                View/edit settings
  bcd admin backup --output <file>  Backup database
  bcd admin barcode-generate        Generate labels

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Next Steps

1. **Start the API server**: `bcd-api serve`
2. **Import your data**:
   - Borrowers: `bcd borrower import students.csv`
   - Catalog: `bcd catalog import bibliographic.csv`
3. **Generate barcodes**: `bcd admin barcode-generate --all`
4. **Start circulating**: `bcd checkout` (interactive mode)

For detailed API documentation, see `contracts/api-spec.yaml`.

---

**Version**: 1.0.0 | **Last Updated**: 2026-01-30
