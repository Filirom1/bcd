/**
 * Composable for fetching borrower data from the API.
 * @ts-check
 */

import { apiClient } from '../api/client.js';
import { normalizeCollection } from '../models/pagination.js';

/** @typedef {import('../models/borrower.js').Borrower} Borrower */

const { ref } = Vue;

/**
 * Composable for fetching borrower data from the API.
 *
 * Provides reusable functions for loading borrowers with optional filtering.
 */
export function useBorrowerData() {
    /**
     * Fetch borrowers from the API.
     *
     * @param {string|null} classIds - Optional class ID to filter by
     * @param {number} pageSize - Number of borrowers to fetch (default: 500)
     * @returns {Promise<Borrower[]>} Array of borrower objects
     * @throws {Error} If the API request fails
     */
    const fetchBorrowers = async (classIds = null, pageSize = 500) => {
        /** @type {Record<string, any>} */
        const params = {
            page: 1,
            page_size: pageSize
        };

        if (classIds) {
            params.class_id = classIds;
        }

        try {
            const data = await apiClient.get('/borrowers', params);
            const normalized = normalizeCollection(data);
            return normalized.items;
        } catch (error) {
            throw new Error('Failed to load borrowers');
        }
    };

    return { fetchBorrowers };
}
