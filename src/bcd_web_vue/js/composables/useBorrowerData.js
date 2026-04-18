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
     * @returns {Promise<Array>} Array of borrower objects
     * @throws {Error} If the API request fails
     */
    const fetchBorrowers = async (classIds = null, pageSize = 500) => {
        const params = new URLSearchParams({
            page: 1,
            page_size: pageSize
        });

        if (classIds) {
            params.set('class_id', classIds);
        }

        const response = await fetch(`/api/v1/borrowers?${params}`);
        if (!response.ok) {
            throw new Error('Failed to load borrowers');
        }

        const data = await response.json();
        return data.items || data.borrowers || [];
    };

    /**
     * Fetch system settings from the API.
     *
     * @returns {Promise<Object|null>} Settings object or null if request fails
     */
    const fetchSettings = async () => {
        try {
            const response = await fetch('/api/v1/admin/settings');
            if (response.ok) {
                return await response.json();
            }
        } catch (err) {
            console.error('Failed to load settings:', err);
        }
        return null;
    };

    return { fetchBorrowers, fetchSettings };
}
