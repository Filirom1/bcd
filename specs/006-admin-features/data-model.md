# Data Model: Admin Features

**Feature**: 006-admin-features
**Date**: 2026-02-07
**Version**: 1.0.0

## Overview

This document defines the database schema and entity relationships for the admin features. **No new tables are required** - all admin operations use existing models (Class, Borrower, BiblographicRecord, Item) with documented CASCADE delete behavior.

---

## Entity Definitions

### Class

**Table**: `class`
**Purpose**: Represents a school class/grade level grouping for students

**Columns**:

| Column | Type | Constraints | Index | Description |
|--------|------|-------------|-------|-------------|
| `id` | Integer | PRIMARY KEY, AUTO_INCREMENT | ✅ | Internal ID |
| `name` | String(50) | NOT NULL | ✅ | Class name (e.g., "CP-A", "CE1-B") |
| `grade_level` | String(20) | NOT NULL | ✅ | Grade level (CP, CE1, CE2, CM1, CM2) |
| `academic_year` | String(9) | NOT NULL | ✅ | Academic year (e.g., "2025-2026") |
| `homeroom_teacher` | String(100) | NULL | ❌ | Homeroom teacher name |
| `notes` | Text | NULL | ❌ | Administrative notes |
| `created_at` | DateTime | NOT NULL, DEFAULT UTC | ❌ | Creation timestamp |
| `updated_at` | DateTime | NOT NULL, DEFAULT UTC, ON UPDATE UTC | ❌ | Last update timestamp |

**Constraints**:
- `UNIQUE(name, academic_year)` - Class name must be unique per academic year

**Relationships**:
- `borrowers` → One-to-Many with Borrower (back_populates="class_")

**DELETE Behavior**:
- When a class is deleted:
  - All borrowers in the class have `class_id` set to NULL (via `ondelete="SET NULL"` on Borrower.class_id)
  - No CASCADE delete of borrowers
  - No orphan records created

**Example Data**:
```json
{
  "id": 1,
  "name": "CP-A",
  "grade_level": "CP",
  "academic_year": "2025-2026",
  "homeroom_teacher": "Mme Dubois",
  "notes": "Morning class"
}
```

---

### Borrower

**Table**: `borrower`
**Purpose**: Represents library users (students, teachers, staff)

**Columns**:

| Column | Type | Constraints | Index | Description |
|--------|------|-------------|-------|-------------|
| `id` | Integer | PRIMARY KEY, AUTO_INCREMENT | ✅ | Internal ID |
| `borrower_id` | String(20) | NOT NULL, UNIQUE | ✅ | User-facing ID (student ID, employee ID) |
| `first_name` | String(100) | NOT NULL | ❌ | First name |
| `last_name` | String(100) | NOT NULL | ❌ | Last name |
| `full_name` | String(200) | NOT NULL | ✅ | Full name (computed: "First LAST") |
| `role` | String(20) | NOT NULL, CHECK IN ('student','teacher','staff') | ✅ | Borrower role |
| `class_id` | Integer | FK(class.id) ON DELETE SET NULL, NULL | ✅ | Class assignment (students only) |
| `grade_level` | String(20) | NULL | ❌ | Grade level (denormalized from class) |
| `barcode` | String(50) | NOT NULL, UNIQUE | ✅ | Barcode for scanning |
| `active` | Boolean | NOT NULL, DEFAULT TRUE | ✅ | Active status |
| `blocked_reason` | String(200) | NULL | ❌ | Reason if blocked |
| `email` | String(100) | NULL | ❌ | Email address |
| `phone` | String(20) | NULL | ❌ | Phone number |
| `notes` | Text | NULL | ❌ | Administrative notes |
| `created_at` | DateTime | NOT NULL, DEFAULT UTC | ❌ | Creation timestamp |
| `updated_at` | DateTime | NOT NULL, DEFAULT UTC, ON UPDATE UTC | ❌ | Last update timestamp |

**Relationships**:
- `class_` → Many-to-One with Class (back_populates="borrowers")
- `circulation_transactions` → One-to-Many with CirculationTransaction (cascade="all, delete-orphan")
- `holds` → One-to-Many with Hold (cascade="all, delete-orphan")

**DELETE Behavior**:
- When a borrower is deleted:
  - All circulation transactions are deleted (CASCADE)
  - All holds are deleted (CASCADE)
  - No items are deleted
  - No bibliographic records are deleted

**BULK EDIT Operations**:
- Change class: Update `class_id` for multiple borrowers
- Change role: Update `role` for multiple borrowers
- Delete: Delete multiple borrowers (CASCADE deletes circulation history)

**Example Data**:
```json
{
  "id": 123,
  "borrower_id": "101",
  "first_name": "Amira",
  "last_name": "BENALI",
  "full_name": "Amira BENALI",
  "role": "student",
  "class_id": 1,
  "grade_level": "CP",
  "barcode": "BOR-101",
  "active": true,
  "blocked_reason": null,
  "email": null,
  "phone": null,
  "notes": null
}
```

---

### BiblographicRecord

**Table**: `bibliographic_record`
**Purpose**: Represents the intellectual content/metadata of a title

**Columns** (relevant to admin operations):

| Column | Type | Constraints | Index | Description |
|--------|------|-------------|-------|-------------|
| `id` | Integer | PRIMARY KEY, AUTO_INCREMENT | ✅ | Internal ID |
| `isbn` | String(17) | NULL | ✅ | ISBN-10 or ISBN-13 |
| `title` | String(500) | NOT NULL | ✅ | Title |
| `subtitle` | String(500) | NULL | ❌ | Subtitle |
| `authors` | Text (JSON array) | NULL | ❌ | Authors JSON array |
| `illustrators` | Text (JSON array) | NULL | ❌ | Illustrators JSON array |
| `publisher` | String(200) | NULL | ❌ | Publisher |
| `publication_year` | Integer | NULL | ✅ | Publication year |
| `language` | String(10) | NULL | ✅ | Language code (fr, en, etc.) |
| `category` | String(100) | NULL | ✅ | Category |
| `genre` | String(100) | NULL | ✅ | Genre |
| `medium_type` | String(50) | NOT NULL | ✅ | Medium type (book, CD, DVD, etc.) |
| `target_audience` | String(20) | NULL, CHECK IN ('child','youth','adult') | ✅ | Target audience |
| `description` | Text | NULL | ❌ | Description |
| `total_items` | Integer | NOT NULL, DEFAULT 0 | ❌ | Denormalized item count |
| `total_circulations` | Integer | NOT NULL, DEFAULT 0 | ❌ | Denormalized circulation count |
| `created_at` | DateTime | NOT NULL, DEFAULT UTC | ❌ | Creation timestamp |
| `updated_at` | DateTime | NOT NULL, DEFAULT UTC, ON UPDATE UTC | ❌ | Last update timestamp |

**Relationships**:
- `items` → One-to-Many with Item (cascade="all, delete-orphan")
- `circulation_transactions` → One-to-Many with CirculationTransaction (cascade="all, delete-orphan")
- `holds` → One-to-Many with Hold (cascade="all, delete-orphan")

**DELETE Behavior**:
- When a bibliographic record is deleted:
  - All items are deleted (CASCADE)
  - All circulation transactions are deleted (CASCADE)
  - All holds are deleted (CASCADE)

**BULK EDIT Operations**:
- Edit common fields: Update `category`, `genre`, `target_audience`, `language` for multiple records
- Delete: Delete multiple records (CASCADE deletes items and circulation history)

**Example Data**:
```json
{
  "id": 456,
  "isbn": "978-2-211-03592-8",
  "title": "Le Loup Est Revenu",
  "subtitle": null,
  "authors": "[\"Geoffroy de Pennart\"]",
  "publisher": "École des loisirs",
  "publication_year": 1994,
  "language": "fr",
  "category": "Fiction",
  "genre": "Conte",
  "medium_type": "Livre",
  "target_audience": "child",
  "description": "Un soir, Monsieur Lapin entend frapper...",
  "total_items": 3,
  "total_circulations": 42
}
```

---

### Item

**Table**: `item`
**Purpose**: Represents a physical copy of a bibliographic record

**Columns**:

| Column | Type | Constraints | Index | Description |
|--------|------|-------------|-------|-------------|
| `id` | Integer | PRIMARY KEY, AUTO_INCREMENT | ✅ | Internal ID |
| `item_id` | String(20) | NOT NULL, UNIQUE | ✅ | Barcode/item ID |
| `bibliographic_record_id` | Integer | FK(bibliographic_record.id) ON DELETE CASCADE, NOT NULL | ✅ | Parent record |
| `call_number` | String(50) | NULL | ✅ | Call number |
| `shelf_location` | String(100) | NULL | ❌ | Shelf location |
| `condition` | String(20) | NOT NULL, DEFAULT 'good', CHECK IN ('good','damaged','lost','withdrawn') | ✅ | Physical condition |
| `status` | String(20) | NOT NULL, DEFAULT 'available', CHECK IN ('available','on_loan','on_hold','in_repair','lost','withdrawn') | ✅ | Status |
| `loanable` | Boolean | NOT NULL, DEFAULT TRUE | ✅ | Can be loaned |
| `acquisition_date` | Date | NULL | ❌ | Acquisition date |
| `funding_source` | String(100) | NULL | ❌ | Funding source |
| `circulation_count` | Integer | NOT NULL, DEFAULT 0 | ❌ | Denormalized circulation count |
| `last_borrowed_at` | DateTime | NULL | ❌ | Last borrowed timestamp |
| `created_at` | DateTime | NOT NULL, DEFAULT UTC | ❌ | Creation timestamp |
| `updated_at` | DateTime | NOT NULL, DEFAULT UTC, ON UPDATE UTC | ❌ | Last update timestamp |

**Relationships**:
- `bibliographic_record` → Many-to-One with BiblographicRecord (back_populates="items")
- `circulation_transactions` → One-to-Many with CirculationTransaction (cascade="all, delete-orphan")

**DELETE Behavior**:
- When an item is deleted:
  - All circulation transactions are deleted (CASCADE)
  - Parent bibliographic record is NOT deleted

**BULK EDIT Operations**:
- Edit common fields: Update `shelf_location`, `condition`, `loanable` for multiple items
- Delete: Delete multiple items (CASCADE deletes circulation history)

**Example Data**:
```json
{
  "id": 789,
  "item_id": "ITEM-001",
  "bibliographic_record_id": 456,
  "call_number": "A PEN",
  "shelf_location": "Fiction - CP",
  "condition": "good",
  "status": "available",
  "loanable": true,
  "acquisition_date": "2024-09-01",
  "funding_source": "BCD Budget 2024",
  "circulation_count": 14,
  "last_borrowed_at": "2025-01-15T14:30:00Z"
}
```

---

## CASCADE Delete Rules Summary

| Delete Operation | Cascading Effects | Unaffected Entities |
|------------------|-------------------|---------------------|
| **Delete Class** | - Borrowers: `class_id` → NULL<br>- No other cascades | - Borrowers remain<br>- All circulation history preserved |
| **Delete Borrower** | - CirculationTransactions: CASCADE DELETE<br>- Holds: CASCADE DELETE | - Items remain<br>- BiblographicRecords remain<br>- Classes remain |
| **Delete BiblographicRecord** | - Items: CASCADE DELETE<br>- CirculationTransactions: CASCADE DELETE<br>- Holds: CASCADE DELETE | - Borrowers remain<br>- Classes remain |
| **Delete Item** | - CirculationTransactions: CASCADE DELETE | - BiblographicRecord remains<br>- Borrowers remain |

**Verification**:
- ✅ All CASCADE relationships defined in SQLAlchemy models
- ✅ `ondelete="CASCADE"` enforced at database level (Item.bibliographic_record_id)
- ✅ `ondelete="SET NULL"` enforced at database level (Borrower.class_id)
- ✅ ORM cascade="all, delete-orphan" for all one-to-many relationships
- ✅ No soft deletes (no `deleted_at` column)
- ✅ Atomic transactions ensure all-or-nothing deletes

---

## Bulk Operation Data Structures

### Bulk Borrower Operations

**Change Class**:
```json
{
  "operation": "change_class",
  "borrower_ids": [123, 124, 125],
  "target_class_id": 2
}
```

**Change Role**:
```json
{
  "operation": "change_role",
  "borrower_ids": [123, 124, 125],
  "target_role": "teacher"
}
```

**Delete Borrowers**:
```json
{
  "operation": "delete",
  "borrower_ids": [123, 124, 125]
}
```

### Bulk Catalog Operations

**Edit Common Fields**:
```json
{
  "operation": "edit_fields",
  "record_ids": [456, 457, 458],
  "fields": {
    "category": "Fiction",
    "target_audience": "child",
    "language": "fr"
  }
}
```

**Delete Records**:
```json
{
  "operation": "delete",
  "record_ids": [456, 457, 458]
}
```

---

## Indexing Strategy

All admin operations are optimized with comprehensive indexing:

**Class Table**:
- ✅ `id` (PRIMARY KEY)
- ✅ `name` (for search/filtering)
- ✅ `grade_level` (for filtering)
- ✅ `academic_year` (for filtering)

**Borrower Table**:
- ✅ `id` (PRIMARY KEY)
- ✅ `borrower_id` (for lookup)
- ✅ `full_name` (for search/sorting)
- ✅ `role` (for filtering)
- ✅ `class_id` (for JOIN with Class)
- ✅ `active` (for filtering)
- ✅ `barcode` (for scanning)

**BiblographicRecord Table**:
- ✅ `id` (PRIMARY KEY)
- ✅ `isbn` (for lookup)
- ✅ `title` (for search/sorting)
- ✅ `category` (for filtering)
- ✅ `genre` (for filtering)
- ✅ `medium_type` (for filtering)
- ✅ `target_audience` (for filtering)
- ✅ `language` (for filtering)
- ✅ `publication_year` (for sorting)

**Item Table**:
- ✅ `id` (PRIMARY KEY)
- ✅ `item_id` (for lookup)
- ✅ `bibliographic_record_id` (for JOIN with BiblographicRecord)
- ✅ `call_number` (for sorting)
- ✅ `condition` (for filtering)
- ✅ `status` (for filtering)
- ✅ `loanable` (for filtering)

**Performance Impact**:
- All foreign keys are indexed → Fast JOINs
- All filter fields are indexed → Fast WHERE clauses
- All sort fields are indexed → Fast ORDER BY
- Bulk operations use single transaction → No N+1 queries

---

## Migration Requirements

**No migrations needed** - All admin features use existing schema.

**Future migrations** (if soft deletes added later):
- Add `deleted_at` column to Borrower, BiblographicRecord, Item
- Add index on `deleted_at`
- Update all queries to filter `WHERE deleted_at IS NULL`

**Backward compatibility**:
- Existing API endpoints unchanged
- Existing service methods unchanged
- New admin endpoints are additive

---

## Data Integrity Constraints

### Atomic Transactions

All bulk operations run in a single database transaction:

```python
# Service-layer pattern
def bulk_delete_borrowers(db: Session, borrower_ids: list[int]) -> BulkOperationResult:
    try:
        # Validate all IDs exist
        borrowers = db.query(Borrower).filter(Borrower.id.in_(borrower_ids)).all()

        if len(borrowers) != len(borrower_ids):
            raise ValidationError("Some borrower IDs not found")

        # Delete all (CASCADE deletes circulation transactions)
        for borrower in borrowers:
            db.delete(borrower)

        # Commit transaction (all-or-nothing)
        db.commit()

        return BulkOperationResult(
            total_count=len(borrower_ids),
            successful_count=len(borrower_ids),
            failed_count=0
        )
    except Exception as e:
        db.rollback()  # Rollback on any error
        raise BulkOperationFailedException(...)
```

### Validation Rules

**Class Deletion**:
- ✅ Class can be deleted even if it has borrowers
- ✅ Borrowers are unassigned (class_id → NULL)
- ❌ Cannot delete if class does not exist (404)

**Borrower Deletion**:
- ✅ Can delete borrowers with circulation history (CASCADE deletes transactions)
- ✅ Can delete borrowers with active loans (CASCADE deletes transactions)
- ❌ Cannot delete if borrower does not exist (404)

**Catalog Record Deletion**:
- ✅ Can delete records with items (CASCADE deletes items)
- ✅ Can delete records with circulation history (CASCADE deletes transactions)
- ❌ Cannot delete if record does not exist (404)

**Item Deletion**:
- ✅ Can delete items with circulation history (CASCADE deletes transactions)
- ⚠️ **Warning**: Deleting items on loan will orphan the loan record (transaction deleted)
- ❌ Cannot delete if item does not exist (404)

---

## Performance Considerations

**Bulk Operations**:
- Target: <10 seconds for 100 records on legacy hardware
- Use single transaction for atomic commit
- No N+1 query pattern (use `filter().all()` not loop queries)
- Progress indicator for 100+ records

**Denormalized Counters**:
- `BiblographicRecord.total_items` updated when items added/deleted
- `BiblographicRecord.total_circulations` updated on checkout
- Enables fast filtering without COUNT queries

**Indexing**:
- All foreign keys indexed → Fast CASCADE deletes
- All filter fields indexed → Fast bulk selection
- All sort fields indexed → Fast result ordering

---

## Document Status

**Status**: ✅ Complete
**Reviewed**: 2026-02-07
**Next Steps**: Generate contracts/api-endpoints.yaml

---

**Related Documents**:
- [plan.md](./plan.md) - Implementation plan
- [research.md](./research.md) - Research findings
- [contracts/api-endpoints.yaml](./contracts/api-endpoints.yaml) - API contract (next artifact)
