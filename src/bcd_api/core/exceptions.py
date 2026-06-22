"""Custom exceptions for BCD library system."""

from typing import Any, Optional

from fastapi import HTTPException, status


class BCDException(HTTPException):
    """Base exception for BCD application with error code and context support."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.context = context or {}


class NotFoundException(BCDException):
    """Exception raised when a resource is not found."""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found: {identifier}"
        )


class ValidationError(BCDException):
    """Exception raised when validation fails."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class ConflictError(BCDException):
    """Exception raised when there's a conflict (e.g., duplicate)."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class BusinessRuleViolation(BCDException):
    """Exception raised when a business rule is violated."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )


# Specific exceptions for common scenarios

class BorrowerNotFoundException(NotFoundException):
    """Borrower not found."""

    def __init__(self, borrower_id: str):
        super().__init__("Borrower", borrower_id)
        self.error_code = "BORROWER_NOT_FOUND"
        self.context = {"borrower_id": borrower_id}


class BorrowerHasOverdueItemsException(BusinessRuleViolation):
    """Borrower has overdue items and cannot check out."""

    def __init__(self, borrower_id: str, overdue_count: int):
        detail = f"Borrower has {overdue_count} overdue item(s). Cannot checkout until overdue items are returned."
        context = {"borrower_id": borrower_id, "overdue_count": overdue_count}
        super().__init__(detail)
        self.error_code = "BORROWER_HAS_OVERDUE"
        self.context = context


class BorrowerBlockedException(BusinessRuleViolation):
    """Borrower is blocked."""

    def __init__(self, borrower_id: str, reason: str):
        detail = f"Borrower {borrower_id} is blocked: {reason}"
        context = {"borrower_id": borrower_id, "reason": reason}
        super().__init__(detail)
        self.error_code = "BORROWER_BLOCKED"
        self.context = context


class ItemNotFoundException(NotFoundException):
    """Item not found."""

    def __init__(self, item_id: str):
        super().__init__("Item", item_id)
        self.error_code = "ITEM_NOT_FOUND"
        self.context = {"item_id": item_id}


class ItemNotAvailableException(BusinessRuleViolation):
    """Item is not available for checkout."""

    def __init__(self, item_id: str, current_status: str):
        detail = f"Item {item_id} is not available (current status: {current_status})"
        context = {"item_id": item_id, "status": current_status}
        super().__init__(detail)
        self.error_code = "ITEM_NOT_AVAILABLE"
        self.context = context


class ItemNotLoanableException(BusinessRuleViolation):
    """Item cannot be loaned."""

    def __init__(self, item_id: str):
        detail = f"Item {item_id} is marked as not loanable"
        context = {"item_id": item_id}
        super().__init__(detail)
        self.error_code = "ITEM_NOT_LOANABLE"
        self.context = context


class ItemAlreadyOnLoanException(ConflictError):
    """Item is already checked out."""

    def __init__(self, item_id: str, borrower_name: str, due_date: str):
        detail = f"Item {item_id} is already on loan to {borrower_name} (due {due_date})"
        context = {
            "item_id": item_id,
            "borrower_name": borrower_name,
            "due_date": str(due_date)
        }
        super().__init__(detail)
        self.error_code = "ITEM_ALREADY_ON_LOAN"
        self.context = context


class ItemReservedForOtherBorrowerException(ConflictError):
    """Item is reserved (hold ready) for another borrower."""

    def __init__(self, item_id: str, reserved_for_name: str):
        detail = f"Item {item_id} is reserved for {reserved_for_name}"
        context = {"item_id": item_id, "reserved_for_name": reserved_for_name}
        super().__init__(detail)
        self.error_code = "ITEM_RESERVED_FOR_OTHER"
        self.context = context


class ItemNotOnLoanException(BusinessRuleViolation):
    """Item is not currently on loan."""

    def __init__(self, item_id: str):
        detail = f"Item {item_id} is not currently on loan"
        context = {"item_id": item_id}
        super().__init__(detail)
        self.error_code = "ITEM_NOT_ON_LOAN"
        self.context = context


class LoanLimitExceededException(BusinessRuleViolation):
    """Borrower has exceeded loan limit."""

    def __init__(self, borrower_id: str, current_count: int, limit: int, additional: int = 1):
        # Simple message without grammar issues
        detail = f"Loan limit reached: {current_count}/{limit} items checked out. Cannot check out more items."
        context = {
            "borrower_id": borrower_id,
            "current": current_count,
            "limit": limit,
            "additional": additional
        }
        super().__init__(detail)
        self.error_code = "LOAN_LIMIT_EXCEEDED"
        self.context = context


class RenewalLimitExceededException(BusinessRuleViolation):
    """Item has exceeded renewal limit."""

    def __init__(self, item_id: str, current_renewals: int, limit: int):
        detail = f"Item {item_id} has reached renewal limit ({current_renewals}/{limit})"
        context = {"item_id": item_id, "current_renewals": current_renewals, "limit": limit}
        super().__init__(detail)
        self.error_code = "RENEWAL_LIMIT_EXCEEDED"
        self.context = context


class NoRenewableItemsException(BusinessRuleViolation):
    """No items available for renewal."""

    def __init__(self, borrower_id: str):
        detail = "No items to renew. Either specify item IDs or borrower has no renewable items."
        context = {"borrower_id": borrower_id}
        super().__init__(detail)
        self.error_code = "NO_RENEWABLE_ITEMS"
        self.context = context


class ItemHasHoldsException(BusinessRuleViolation):
    """Item has pending holds and cannot be renewed."""

    def __init__(self, item_id: str, holds_count: int):
        super().__init__(
            f"Item {item_id} has {holds_count} pending hold(s) and cannot be renewed"
        )


class BiblographicRecordNotFoundException(NotFoundException):
    """Bibliographic record not found."""

    def __init__(self, biblio_id: int):
        super().__init__("Bibliographic record", biblio_id)


class DuplicateISBNException(ConflictError):
    """ISBN already exists."""

    def __init__(self, isbn: str, existing_id: int):
        super().__init__(
            f"ISBN {isbn} already exists (Bibliographic record ID: {existing_id})"
        )


class DuplicateBorrowerIDException(ConflictError):
    """Borrower ID already exists."""

    def __init__(self, borrower_id: str):
        super().__init__(
            f"Borrower ID {borrower_id} already exists"
        )


class DuplicateItemIDException(ConflictError):
    """Item ID already exists."""

    def __init__(self, item_id: str):
        super().__init__(
            f"Item ID {item_id} already exists"
        )
        self.error_code = "DUPLICATE_ITEM_ID"


class InvalidIDFormatException(ValidationError):
    """ID format is invalid."""

    def __init__(self, id_type: str, value: str, expected_format: str):
        super().__init__(
            f"Invalid {id_type} format: '{value}' (expected: {expected_format})"
        )


class ExportTooLargeException(BusinessRuleViolation):
    """Export exceeds maximum row limit."""

    def __init__(self, record_count: int, limit: int = 10000):
        detail = f"Export contains {record_count} records, exceeding the maximum limit of {limit} rows."
        context = {
            "record_count": record_count,
            "limit": limit,
            "suggestion": "Consider filtering the catalog or exporting in smaller batches."
        }
        super().__init__(detail)
        self.error_code = "EXPORT_TOO_LARGE"
        self.context = context


class ExportFailedException(BCDException):
    """Export operation failed due to an error."""

    def __init__(self, reason: str, details: Optional[dict] = None):
        detail = f"Export failed: {reason}"
        context = details or {}
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail
        )
        self.error_code = "EXPORT_FAILED"
        self.context = context


# CSV Import/Export specific exceptions

class CSVValidationError(ValidationError):
    """CSV validation failed."""

    def __init__(self, detail: str, row_number: Optional[int] = None, column: Optional[str] = None):
        context = {}
        if row_number is not None:
            context["row_number"] = row_number
            detail = f"Row {row_number}: {detail}"
        if column:
            context["column"] = column
        super().__init__(detail)
        self.error_code = "CSV_VALIDATION_ERROR"
        self.context = context


class CSVEncodingError(BusinessRuleViolation):
    """CSV encoding detection or decoding failed."""

    def __init__(self, filename: str, attempted_encodings: Optional[list] = None):
        attempted = ", ".join(attempted_encodings) if attempted_encodings else "UTF-8, Windows-1252, Latin-1"
        detail = f"Could not decode CSV file '{filename}'. Tried encodings: {attempted}"
        context = {
            "filename": filename,
            "attempted_encodings": attempted_encodings or ["utf-8", "windows-1252", "latin-1"]
        }
        super().__init__(detail)
        self.error_code = "CSV_ENCODING_ERROR"
        self.context = context


class CSVRowLimitError(BusinessRuleViolation):
    """CSV exceeds maximum row limit."""

    def __init__(self, row_count: int, limit: int, entity_type: str = "records"):
        detail = f"CSV contains {row_count} {entity_type}, exceeding the maximum limit of {limit} rows."
        context = {
            "row_count": row_count,
            "limit": limit,
            "entity_type": entity_type
        }
        super().__init__(detail)
        self.error_code = "CSV_ROW_LIMIT_EXCEEDED"
        self.context = context


# Admin-specific exceptions

class ClassHasBorrowersException(BusinessRuleViolation):
    """Class has borrowers assigned and cannot be deleted."""

    def __init__(self, class_id: int, class_name: str, borrower_count: int):
        detail = f"Class '{class_name}' has {borrower_count} borrower(s) assigned and cannot be deleted"
        context = {
            "class_id": class_id,
            "class_name": class_name,
            "borrower_count": borrower_count,
            "suggestion": "Unassign borrowers from the class before deleting"
        }
        super().__init__(detail)
        self.error_code = "CLASS_HAS_BORROWERS"
        self.context = context


class BorrowerHasActiveLoansException(BusinessRuleViolation):
    """Borrower has active loans and cannot be deleted."""

    def __init__(self, borrower_id: str, borrower_name: str, active_loan_count: int):
        detail = f"Borrower '{borrower_name}' has {active_loan_count} active loan(s) and cannot be deleted"
        context = {
            "borrower_id": borrower_id,
            "borrower_name": borrower_name,
            "active_loan_count": active_loan_count,
            "suggestion": "Return all borrowed items before deleting the borrower"
        }
        super().__init__(detail)
        self.error_code = "BORROWER_HAS_ACTIVE_LOANS"
        self.context = context


class ItemHasActiveLoanException(BusinessRuleViolation):
    """Item is currently on loan and cannot be deleted."""

    def __init__(self, item_id: str, borrower_name: str, due_date: str):
        detail = f"Item {item_id} is currently on loan to {borrower_name} (due {due_date}) and cannot be deleted"
        context = {
            "item_id": item_id,
            "borrower_name": borrower_name,
            "due_date": str(due_date),
            "suggestion": "Wait for the item to be returned before deleting it"
        }
        super().__init__(detail)
        self.error_code = "ITEM_HAS_ACTIVE_LOAN"
        self.context = context


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


class BulkOperationFailedException(BCDException):
    """Bulk operation failed and was rolled back."""

    def __init__(self, operation: str, total_count: int, failed_count: int, errors: list[dict]):
        detail = f"Bulk {operation} failed: {failed_count} of {total_count} records could not be processed"
        context = {
            "operation": operation,
            "total_count": total_count,
            "failed_count": failed_count,
            "successful_count": total_count - failed_count,
            "errors": errors  # List of {"record_id": ..., "error": ...}
        }
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
        self.error_code = "BULK_OPERATION_FAILED"
        self.context = context


class ClassNotFoundException(NotFoundException):
    """Class not found."""

    def __init__(self, class_id: int):
        super().__init__("Class", class_id)
        self.error_code = "CLASS_NOT_FOUND"
        self.context = {"class_id": class_id}


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


class HoldLimitExceededException(BusinessRuleViolation):
    """Borrower has reached the maximum number of active holds."""

    def __init__(self, current: int, limit: int):
        detail = f"Borrower has reached the maximum number of active holds ({limit})"
        context = {"current": current, "limit": limit}
        super().__init__(detail)
        self.error_code = "HOLD_LIMIT_EXCEEDED"
        self.context = context


# Aliases for backward compatibility with generic names
NotFoundError = NotFoundException
DuplicateError = ConflictError
