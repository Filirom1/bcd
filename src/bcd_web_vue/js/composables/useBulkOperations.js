/**
 * useBulkOperations - Bulk edit/delete API calls composable (DRY component)
 *
 * Provides reusable bulk operation logic with progress tracking.
 * Used by BorrowerList, SearchResults, and other components with bulk actions.
 *
 * @param {string} resourceType - Type of resource ('borrowers' or 'catalog')
 * @returns {Object} Bulk operation methods and state
 */

const { ref } = Vue;
import { ApiError } from '../models/error.js';

export function useBulkOperations(resourceType) {
    const loading = ref(false);
    const error = ref(null);
    const progress = ref(0);
    const showProgress = ref(false);

    /**
     * Determine if operation should show progress bar (≥100 items threshold)
     * @param {number} count - Number of items
     * @returns {boolean}
     */
    const shouldShowProgress = (count) => count >= 100;

    /**
     * Bulk change class for borrowers
     * @param {Array<number>} borrowerIds - IDs of borrowers
     * @param {number} targetClassId - Target class ID
     * @returns {Promise<Object>} Operation result
     */
    const bulkChangeClass = async (borrowerIds, targetClassId) => {
        loading.value = true;
        error.value = null;
        showProgress.value = shouldShowProgress(borrowerIds.length);
        progress.value = 0;

        try {
            const response = await fetch('/api/v1/admin/borrowers/bulk-edit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    operation: 'change_class',
                    borrower_ids: borrowerIds,
                    target_class_id: targetClassId
                })
            });

            if (!response.ok) {
                const apiError = await ApiError.fromResponse(response);
                throw apiError;
            }

            progress.value = 100;
            return await response.json();
        } catch (err) {
            error.value = err.message;
            throw err;
        } finally {
            loading.value = false;
            setTimeout(() => {
                showProgress.value = false;
                progress.value = 0;
            }, 500);
        }
    };

    /**
     * Bulk change role for borrowers
     * @param {Array<number>} borrowerIds - IDs of borrowers
     * @param {string} targetRole - Target role (student/teacher/staff)
     * @returns {Promise<Object>} Operation result
     */
    const bulkChangeRole = async (borrowerIds, targetRole) => {
        loading.value = true;
        error.value = null;
        showProgress.value = shouldShowProgress(borrowerIds.length);
        progress.value = 0;

        try {
            const response = await fetch('/api/v1/admin/borrowers/bulk-edit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    operation: 'change_role',
                    borrower_ids: borrowerIds,
                    target_role: targetRole
                })
            });

            if (!response.ok) {
                const apiError = await ApiError.fromResponse(response);
                throw apiError;
            }

            progress.value = 100;
            return await response.json();
        } catch (err) {
            error.value = err.message;
            throw err;
        } finally {
            loading.value = false;
            setTimeout(() => {
                showProgress.value = false;
                progress.value = 0;
            }, 500);
        }
    };

    /**
     * Bulk delete borrowers
     * @param {Array<number>} borrowerIds - IDs of borrowers to delete
     * @returns {Promise<Object>} Operation result
     */
    const bulkDeleteBorrowers = async (borrowerIds) => {
        loading.value = true;
        error.value = null;
        showProgress.value = shouldShowProgress(borrowerIds.length);
        progress.value = 0;

        try {
            const response = await fetch('/api/v1/admin/borrowers/bulk-delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    borrower_ids: borrowerIds
                })
            });

            if (!response.ok) {
                const apiError = await ApiError.fromResponse(response);
                throw apiError;
            }

            progress.value = 100;
            return await response.json();
        } catch (err) {
            error.value = err.message;
            throw err;
        } finally {
            loading.value = false;
            setTimeout(() => {
                showProgress.value = false;
                progress.value = 0;
            }, 500);
        }
    };

    /**
     * Bulk edit catalog records
     * @param {Array<number>} recordIds - IDs of records to edit
     * @param {Object} fields - Fields to update (genre, target_audience, language, medium_type)
     * @returns {Promise<Object>} Operation result
     */
    const bulkEditRecords = async (recordIds, fields) => {
        loading.value = true;
        error.value = null;
        showProgress.value = shouldShowProgress(recordIds.length);
        progress.value = 0;

        try {
            const response = await fetch('/api/v1/admin/catalog/bulk-edit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    record_ids: recordIds,
                    ...fields
                })
            });

            if (!response.ok) {
                const apiError = await ApiError.fromResponse(response);
                throw apiError;
            }

            progress.value = 100;
            return await response.json();
        } catch (err) {
            error.value = err.message;
            throw err;
        } finally {
            loading.value = false;
            setTimeout(() => {
                showProgress.value = false;
                progress.value = 0;
            }, 500);
        }
    };

    /**
     * Bulk delete catalog records
     * @param {Array<number>} recordIds - IDs of records to delete
     * @returns {Promise<Object>} Operation result
     */
    const bulkDeleteRecords = async (recordIds) => {
        loading.value = true;
        error.value = null;
        showProgress.value = shouldShowProgress(recordIds.length);
        progress.value = 0;

        try {
            const response = await fetch('/api/v1/admin/catalog/bulk-delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    record_ids: recordIds
                })
            });

            if (!response.ok) {
                const apiError = await ApiError.fromResponse(response);
                throw apiError;
            }

            progress.value = 100;
            return await response.json();
        } catch (err) {
            error.value = err.message;
            throw err;
        } finally {
            loading.value = false;
            setTimeout(() => {
                showProgress.value = false;
                progress.value = 0;
            }, 500);
        }
    };

    /**
     * Update single record
     * @param {number} recordId - Record ID
     * @param {Object} data - Update data
     * @returns {Promise<Object>} Updated record
     */
    const updateRecord = async (recordId, data) => {
        loading.value = true;
        error.value = null;

        try {
            const response = await fetch(`/api/v1/catalog/records/${recordId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const apiError = await ApiError.fromResponse(response);
                throw apiError;
            }

            return await response.json();
        } catch (err) {
            error.value = err.message;
            throw err;
        } finally {
            loading.value = false;
        }
    };

    /**
     * Update single item
     * @param {number} itemId - Item ID
     * @param {Object} data - Update data
     * @returns {Promise<Object>} Updated item
     */
    const updateItem = async (itemId, data) => {
        loading.value = true;
        error.value = null;

        try {
            const response = await fetch(`/api/v1/catalog/items/${itemId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                const apiError = await ApiError.fromResponse(response);
                throw apiError;
            }

            return await response.json();
        } catch (err) {
            error.value = err.message;
            throw err;
        } finally {
            loading.value = false;
        }
    };

    return {
        loading,
        error,
        progress,
        showProgress,
        // Borrower operations
        bulkChangeClass,
        bulkChangeRole,
        bulkDeleteBorrowers,
        // Catalog operations
        bulkEditRecords,
        bulkDeleteRecords,
        updateRecord,
        updateItem
    };
}
