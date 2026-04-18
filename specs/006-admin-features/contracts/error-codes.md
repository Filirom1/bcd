# Error Codes: Admin Features

**Feature**: 006-admin-features
**Date**: 2026-02-07
**Version**: 1.0.0

## Overview

This document defines all error codes for admin operations, following the established BCDException pattern with structured `error_code` and `context` fields for frontend i18n support.

**Architecture Pattern**: All exceptions inherit from `BCDException` base class and provide:
- `error_code`: Machine-readable string (e.g., `BORROWER_ID_NOT_AVAILABLE`)
- `context`: Dictionary with structured data (e.g., `{"borrower_id": "101", "existing_borrower_name": "Amira BENALI"}`)
- `detail`: Human-readable message (for logging, not user-facing)

**Frontend Flow**:
1. API returns error with `error_code` and `context`
2. Frontend maps `error_code` to i18n translation key (`errors.{error_code}`)
3. Frontend interpolates `context` variables into translated message
4. User sees error in their language (en/fr)

---

## Error Code Categories

### Admin Operations (6 new error codes)

| Error Code | HTTP Status | Category | Use Case |
|------------|-------------|----------|----------|
| `BORROWER_ID_NOT_AVAILABLE` | 409 Conflict | ConflictError | Borrower ID already in use during single edit |
| `DUPLICATE_BARCODE` | 409 Conflict | ConflictError | Item barcode already in use during single edit |
| `BULK_OPERATION_FAILED` | 400 Bad Request | BusinessRuleViolation | Bulk operation failed and rolled back |
| `VALIDATION_FAILED` | 422 Unprocessable Entity | ValidationError | Field validation failed |
| `CLASS_NOT_FOUND` | 404 Not Found | NotFoundException | Class ID not found |
| `DUPLICATE_CLASS_NAME` | 409 Conflict | ConflictError | Class name already exists for academic year |

### Existing Error Codes (reused in admin features)

| Error Code | HTTP Status | Use Case |
|------------|-------------|----------|
| `BORROWER_NOT_FOUND` | 404 Not Found | Borrower ID not found during bulk operations |
| `ITEM_NOT_FOUND` | 404 Not Found | Item ID not found during bulk operations |
| `RECORD_NOT_FOUND` | 404 Not Found | Bibliographic record ID not found |

---

## Error Code Definitions

### BORROWER_ID_NOT_AVAILABLE

**HTTP Status**: 409 Conflict
**Exception Class**: `BorrowerIDNotAvailableException`
**Category**: ConflictError
**Use Case**: Single borrower edit - borrower ID already assigned to another borrower

**Context Fields**:
- `borrower_id` (string): The borrower ID that was attempted
- `existing_borrower_name` (string): Full name of the borrower who owns this ID
- `suggestion` (string): Suggestion for resolution

**Backend Implementation**:
```python
class BorrowerIDNotAvailableException(ConflictError):
    """Borrower ID is already in use by another borrower."""

    def __init__(self, borrower_id: str, existing_borrower_name: str):
        detail = f"Borrower ID '{borrower_id}' is already assigned to {existing_borrower_name}"
        context = {
            "borrower_id": borrower_id,
            "existing_borrower_name": existing_borrower_name,
            "suggestion": "Choose a different ID or update the existing borrower"
        }
        super().__init__(detail)
        self.error_code = "BORROWER_ID_NOT_AVAILABLE"
        self.context = context
```

**API Response Example**:
```json
{
  "detail": "Borrower ID '101' is already assigned to Amira BENALI",
  "error_code": "BORROWER_ID_NOT_AVAILABLE",
  "context": {
    "borrower_id": "101",
    "existing_borrower_name": "Amira BENALI",
    "suggestion": "Choose a different ID or update the existing borrower"
  }
}
```

**Frontend i18n (en)**:
```json
{
  "errors": {
    "BORROWER_ID_NOT_AVAILABLE": "Borrower ID '{{borrower_id}}' is already assigned to {{existing_borrower_name}}. Please choose a different ID."
  }
}
```

**Frontend i18n (fr)**:
```json
{
  "errors": {
    "BORROWER_ID_NOT_AVAILABLE": "L'identifiant emprunteur '{{borrower_id}}' est déjà attribué à {{existing_borrower_name}}. Veuillez choisir un autre identifiant."
  }
}
```

---

### DUPLICATE_BARCODE

**HTTP Status**: 409 Conflict
**Exception Class**: `DuplicateBarcodeException`
**Category**: ConflictError
**Use Case**: Single item edit - item barcode already assigned to another item

**Context Fields**:
- `barcode` (string): The barcode that was attempted
- `existing_item_id` (string): Item ID (barcode) of the item that owns this barcode
- `suggestion` (string): Suggestion for resolution

**Backend Implementation**:
```python
class DuplicateBarcodeException(ConflictError):
    """Item barcode is already in use."""

    def __init__(self, barcode: str, existing_item_id: str):
        detail = f"Barcode '{barcode}' is already assigned to item {existing_item_id}"
        context = {
            "barcode": barcode,
            "existing_item_id": existing_item_id,
            "suggestion": "Use a different barcode or update the existing item"
        }
        super().__init__(detail)
        self.error_code = "DUPLICATE_BARCODE"
        self.context = context
```

**API Response Example**:
```json
{
  "detail": "Barcode 'ITEM-001' is already assigned to item 789",
  "error_code": "DUPLICATE_BARCODE",
  "context": {
    "barcode": "ITEM-001",
    "existing_item_id": "789",
    "suggestion": "Use a different barcode or update the existing item"
  }
}
```

**Frontend i18n (en)**:
```json
{
  "errors": {
    "DUPLICATE_BARCODE": "Barcode '{{barcode}}' is already assigned to item {{existing_item_id}}. Please use a different barcode."
  }
}
```

**Frontend i18n (fr)**:
```json
{
  "errors": {
    "DUPLICATE_BARCODE": "Le code-barres '{{barcode}}' est déjà attribué à l'exemplaire {{existing_item_id}}. Veuillez utiliser un autre code-barres."
  }
}
```

---

### BULK_OPERATION_FAILED

**HTTP Status**: 400 Bad Request
**Exception Class**: `BulkOperationFailedException`
**Category**: BusinessRuleViolation
**Use Case**: Bulk operation failed during processing (transaction rolled back)

**Context Fields**:
- `operation` (string): Operation type (change_class, change_role, delete, edit_fields)
- `total_count` (integer): Total number of records in operation
- `failed_count` (integer): Number of records that failed
- `successful_count` (integer): Number of records that succeeded (always 0 due to rollback)
- `errors` (array): List of error details per failed record
  - `record_id` (integer): Record ID that failed
  - `error` (string): Error message for this record

**Backend Implementation**:
```python
class BulkOperationFailedException(BusinessRuleViolation):
    """Bulk operation failed and was rolled back."""

    def __init__(self, operation: str, total_count: int, failed_count: int, errors: list[dict]):
        detail = f"Bulk {operation} failed: {failed_count} of {total_count} records could not be processed"
        context = {
            "operation": operation,
            "total_count": total_count,
            "failed_count": failed_count,
            "successful_count": 0,  # Always 0 due to transaction rollback
            "errors": errors  # List of {"record_id": ..., "error": ...}
        }
        super().__init__(detail)
        self.error_code = "BULK_OPERATION_FAILED"
        self.context = context
```

**API Response Example**:
```json
{
  "detail": "Bulk change_class failed: 1 of 3 records could not be processed",
  "error_code": "BULK_OPERATION_FAILED",
  "context": {
    "operation": "change_class",
    "total_count": 3,
    "failed_count": 1,
    "successful_count": 0,
    "errors": [
      {
        "record_id": 124,
        "error": "Borrower not found"
      }
    ]
  }
}
```

**Frontend i18n (en)**:
```json
{
  "errors": {
    "BULK_OPERATION_FAILED": "Bulk {{operation}} failed: {{failed_count}} of {{total_count}} records could not be processed. All changes have been rolled back."
  }
}
```

**Frontend i18n (fr)**:
```json
{
  "errors": {
    "BULK_OPERATION_FAILED": "L'opération groupée {{operation}} a échoué : {{failed_count}} sur {{total_count}} enregistrements n'ont pas pu être traités. Toutes les modifications ont été annulées."
  }
}
```

---

### VALIDATION_FAILED

**HTTP Status**: 422 Unprocessable Entity
**Exception Class**: `ValidationFailedException`
**Category**: ValidationError
**Use Case**: Form field validation failed (single or bulk edit)

**Context Fields**:
- `field_errors` (object): Dictionary of field names to error messages
  - Key: Field name (e.g., "borrower_id", "email")
  - Value: Error message (e.g., "Invalid format", "Required field missing")

**Backend Implementation**:
```python
class ValidationFailedException(ValidationError):
    """Validation failed for one or more fields."""

    def __init__(self, field_errors: dict[str, str]):
        detail = f"Validation failed for {len(field_errors)} field(s)"
        context = {
            "field_errors": field_errors  # {"field_name": "error message"}
        }
        super().__init__(detail)
        self.error_code = "VALIDATION_FAILED"
        self.context = context
```

**API Response Example**:
```json
{
  "detail": "Validation failed for 2 field(s)",
  "error_code": "VALIDATION_FAILED",
  "context": {
    "field_errors": {
      "borrower_id": "Invalid format: expected numeric, got 'ABC123'",
      "email": "Invalid email address format"
    }
  }
}
```

**Frontend i18n (en)**:
```json
{
  "errors": {
    "VALIDATION_FAILED": "Validation failed. Please correct the errors and try again."
  }
}
```

**Frontend i18n (fr)**:
```json
{
  "errors": {
    "VALIDATION_FAILED": "La validation a échoué. Veuillez corriger les erreurs et réessayer."
  }
}
```

**Frontend Rendering**:
```javascript
// Display field-specific errors
if (error.code === 'VALIDATION_FAILED') {
  const fieldErrors = error.context.field_errors;
  for (const [field, message] of Object.entries(fieldErrors)) {
    // Highlight field in red and show error message
    showFieldError(field, message);
  }
}
```

---

### CLASS_NOT_FOUND

**HTTP Status**: 404 Not Found
**Exception Class**: `ClassNotFoundException`
**Category**: NotFoundException
**Use Case**: Class ID not found (create/update/delete/bulk operations)

**Context Fields**:
- `class_id` (integer): The class ID that was not found

**Backend Implementation**:
```python
class ClassNotFoundException(NotFoundException):
    """Class not found."""

    def __init__(self, class_id: int):
        super().__init__("Class", class_id)
        self.error_code = "CLASS_NOT_FOUND"
        self.context = {"class_id": class_id}
```

**API Response Example**:
```json
{
  "detail": "Class not found: 999",
  "error_code": "CLASS_NOT_FOUND",
  "context": {
    "class_id": 999
  }
}
```

**Frontend i18n (en)**:
```json
{
  "errors": {
    "CLASS_NOT_FOUND": "Class not found (ID: {{class_id}})."
  }
}
```

**Frontend i18n (fr)**:
```json
{
  "errors": {
    "CLASS_NOT_FOUND": "Classe introuvable (ID : {{class_id}})."
  }
}
```

---

### DUPLICATE_CLASS_NAME

**HTTP Status**: 409 Conflict
**Exception Class**: `DuplicateClassNameException`
**Category**: ConflictError
**Use Case**: Class name already exists for the academic year

**Context Fields**:
- `class_name` (string): The class name that was attempted
- `academic_year` (string): The academic year
- `suggestion` (string): Suggestion for resolution

**Backend Implementation**:
```python
class DuplicateClassNameException(ConflictError):
    """Class name already exists for the academic year."""

    def __init__(self, class_name: str, academic_year: str):
        detail = f"Class '{class_name}' already exists for academic year {academic_year}"
        context = {
            "class_name": class_name,
            "academic_year": academic_year,
            "suggestion": "Use a different class name or update the existing class"
        }
        super().__init__(detail)
        self.error_code = "DUPLICATE_CLASS_NAME"
        self.context = context
```

**API Response Example**:
```json
{
  "detail": "Class 'CP-A' already exists for academic year 2025-2026",
  "error_code": "DUPLICATE_CLASS_NAME",
  "context": {
    "class_name": "CP-A",
    "academic_year": "2025-2026",
    "suggestion": "Use a different class name or update the existing class"
  }
}
```

**Frontend i18n (en)**:
```json
{
  "errors": {
    "DUPLICATE_CLASS_NAME": "Class '{{class_name}}' already exists for academic year {{academic_year}}. Please choose a different name."
  }
}
```

**Frontend i18n (fr)**:
```json
{
  "errors": {
    "DUPLICATE_CLASS_NAME": "La classe '{{class_name}}' existe déjà pour l'année scolaire {{academic_year}}. Veuillez choisir un autre nom."
  }
}
```

---

## Complete i18n Coverage

### English (en.json)

```json
{
  "errors": {
    "BORROWER_ID_NOT_AVAILABLE": "Borrower ID '{{borrower_id}}' is already assigned to {{existing_borrower_name}}. Please choose a different ID.",
    "DUPLICATE_BARCODE": "Barcode '{{barcode}}' is already assigned to item {{existing_item_id}}. Please use a different barcode.",
    "BULK_OPERATION_FAILED": "Bulk {{operation}} failed: {{failed_count}} of {{total_count}} records could not be processed. All changes have been rolled back.",
    "VALIDATION_FAILED": "Validation failed. Please correct the errors and try again.",
    "CLASS_NOT_FOUND": "Class not found (ID: {{class_id}}).",
    "DUPLICATE_CLASS_NAME": "Class '{{class_name}}' already exists for academic year {{academic_year}}. Please choose a different name."
  },
  "admin": {
    "menu_title": "Admin",
    "import_borrowers": "Import Borrowers",
    "export_borrowers": "Export Borrowers",
    "import_catalog": "Import Catalog (Dublin Core)",
    "export_catalog": "Export Catalog",
    "bulk_edit": "Bulk Edit",
    "edit_selected": "Edit Selected",
    "confirm_delete_title": "Confirm Deletion",
    "warning": "Warning",
    "delete_warning_message": "This action is irreversible. All associated data will be permanently deleted.",
    "delete_count_message": "You are about to permanently delete {{count}} {{type}}.",
    "and_n_more": "...and {{count}} more",
    "delete_n_items": "Delete {{count}} {{type}}"
  }
}
```

### French (fr.json)

```json
{
  "errors": {
    "BORROWER_ID_NOT_AVAILABLE": "L'identifiant emprunteur '{{borrower_id}}' est déjà attribué à {{existing_borrower_name}}. Veuillez choisir un autre identifiant.",
    "DUPLICATE_BARCODE": "Le code-barres '{{barcode}}' est déjà attribué à l'exemplaire {{existing_item_id}}. Veuillez utiliser un autre code-barres.",
    "BULK_OPERATION_FAILED": "L'opération groupée {{operation}} a échoué : {{failed_count}} sur {{total_count}} enregistrements n'ont pas pu être traités. Toutes les modifications ont été annulées.",
    "VALIDATION_FAILED": "La validation a échoué. Veuillez corriger les erreurs et réessayer.",
    "CLASS_NOT_FOUND": "Classe introuvable (ID : {{class_id}}).",
    "DUPLICATE_CLASS_NAME": "La classe '{{class_name}}' existe déjà pour l'année scolaire {{academic_year}}. Veuillez choisir un autre nom."
  },
  "admin": {
    "menu_title": "Admin",
    "import_borrowers": "Importer emprunteurs",
    "export_borrowers": "Exporter emprunteurs",
    "import_catalog": "Importer catalogue (Dublin Core)",
    "export_catalog": "Exporter catalogue",
    "bulk_edit": "Modification groupée",
    "edit_selected": "Modifier sélection",
    "confirm_delete_title": "Confirmer la suppression",
    "warning": "Attention",
    "delete_warning_message": "Cette action est irréversible. Toutes les données associées seront définitivement supprimées.",
    "delete_count_message": "Vous êtes sur le point de supprimer définitivement {{count}} {{type}}.",
    "and_n_more": "...et {{count}} de plus",
    "delete_n_items": "Supprimer {{count}} {{type}}"
  }
}
```

---

## Error Code Summary Table

| Error Code | HTTP | Exception Class | Context Fields | Use Case |
|------------|------|----------------|----------------|----------|
| `BORROWER_ID_NOT_AVAILABLE` | 409 | `BorrowerIDNotAvailableException` | borrower_id, existing_borrower_name, suggestion | Single borrower edit - ID conflict |
| `DUPLICATE_BARCODE` | 409 | `DuplicateBarcodeException` | barcode, existing_item_id, suggestion | Single item edit - barcode conflict |
| `BULK_OPERATION_FAILED` | 400 | `BulkOperationFailedException` | operation, total_count, failed_count, successful_count, errors[] | Bulk operation rollback |
| `VALIDATION_FAILED` | 422 | `ValidationFailedException` | field_errors{} | Form validation errors |
| `CLASS_NOT_FOUND` | 404 | `ClassNotFoundException` | class_id | Class CRUD operations |
| `DUPLICATE_CLASS_NAME` | 409 | `DuplicateClassNameException` | class_name, academic_year, suggestion | Class creation/update |

---

## Frontend Integration

### Error Handling Pattern

```javascript
// src/bcd_web_vue/js/utils/apiClient.js

import { ApiError } from '../models/error.js';

async function handleApiError(response) {
  const data = await response.json();
  const errorCode = data.error_code ? data.error_code.toLowerCase() : 'unknown_error';

  return new ApiError(
    errorCode,
    data.detail,
    data.context || {},
    response.status
  );
}

// Usage in component
try {
  await api.patch(`/borrowers/${borrowerId}`, { borrower_id: newId });
} catch (err) {
  if (err instanceof ApiError) {
    const message = err.getTranslatedMessage(t); // Uses error_code + context
    showError(message);

    // For VALIDATION_FAILED, show field-specific errors
    if (err.code === 'VALIDATION_FAILED') {
      const fieldErrors = err.context.field_errors;
      for (const [field, message] of Object.entries(fieldErrors)) {
        highlightField(field, message);
      }
    }
  }
}
```

### Translation Pattern

```javascript
// src/bcd_web_vue/js/models/error.js

export class ApiError extends Error {
  constructor(code, message, context = {}, statusCode = 500) {
    super(message);
    this.code = code;  // e.g., "borrower_id_not_available"
    this.context = context;  // e.g., {borrower_id: "101", existing_borrower_name: "Amira BENALI"}
    this.statusCode = statusCode;
  }

  /**
   * Get translated error message with variable interpolation
   */
  getTranslatedMessage(t) {
    const key = `errors.${this.code.toUpperCase()}`;  // e.g., "errors.BORROWER_ID_NOT_AVAILABLE"
    const translated = t(key, this.context);  // Vue-i18n with variables

    // Fallback if translation missing
    if (translated === key) {
      return this.message || t('errors.unknown_error');
    }

    return translated;
  }
}
```

---

## Testing Requirements

### Service-Layer Tests

```python
# tests/integration/services/test_admin_operations.py

def test_update_borrower_duplicate_id_raises_exception(db_session):
    """Test that updating borrower ID to duplicate raises BorrowerIDNotAvailableException."""
    # Arrange
    borrower1 = create_test_borrower(db_session, borrower_id="101", full_name="Amira BENALI")
    borrower2 = create_test_borrower(db_session, borrower_id="102", full_name="Lucas MARTIN")

    # Act & Assert
    with pytest.raises(BorrowerIDNotAvailableException) as exc:
        borrower_service.update_borrower(
            db=db_session,
            borrower_id=borrower2.id,
            new_borrower_id="101"  # Duplicate ID
        )

    # Verify exception context
    assert exc.value.error_code == "BORROWER_ID_NOT_AVAILABLE"
    assert exc.value.context["borrower_id"] == "101"
    assert exc.value.context["existing_borrower_name"] == "Amira BENALI"


def test_bulk_delete_borrowers_rollback_on_error(db_session):
    """Test that bulk delete rolls back on error (atomic transaction)."""
    # Arrange
    borrower1 = create_test_borrower(db_session, borrower_id="101")
    borrower2 = create_test_borrower(db_session, borrower_id="102")
    invalid_id = 999999  # Non-existent ID

    # Act & Assert
    with pytest.raises(BulkOperationFailedException) as exc:
        borrower_service.bulk_delete_borrowers(
            db=db_session,
            borrower_ids=[borrower1.id, borrower2.id, invalid_id]
        )

    # Verify exception context
    assert exc.value.error_code == "BULK_OPERATION_FAILED"
    assert exc.value.context["operation"] == "delete"
    assert exc.value.context["total_count"] == 3
    assert exc.value.context["failed_count"] > 0

    # Verify rollback - borrowers still exist
    assert db_session.query(Borrower).filter_by(id=borrower1.id).first() is not None
    assert db_session.query(Borrower).filter_by(id=borrower2.id).first() is not None
```

---

## Document Status

**Status**: ✅ Complete
**Reviewed**: 2026-02-07
**Next Steps**: Generate quickstart.md

---

**Related Documents**:
- [data-model.md](../data-model.md) - Database schema
- [api-endpoints.yaml](./api-endpoints.yaml) - API contract
- [quickstart.md](../quickstart.md) - Developer guide (next artifact)
- [../../.specify/architecture-patterns.md](../../.specify/architecture-patterns.md) - Error handling patterns
