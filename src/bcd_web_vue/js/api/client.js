/**
 * Centralized API client for BCD REST API
 * Handles all HTTP requests with loading state, error handling, and i18n headers
 */

import { ApiError, ERROR_CODES } from '../models/error.js';

/**
 * API Client class
 */
export class ApiClient {
    /**
     * @param {string} baseURL - Base URL for API (default: /api/v1 - proxied through web server)
     * @param {Object} options - Configuration options
     * @param {Function} [options.onLoadingChange] - Callback when loading state changes
     * @param {Function} [options.getLocale] - Function to get current locale
     */
    constructor(baseURL = '/api/v1', options = {}) {
        this.baseURL = baseURL;
        this.onLoadingChange = options.onLoadingChange || (() => {});
        this.getLocale = options.getLocale || (() => 'fr');
        this.activeRequests = 0;
    }

    /**
     * Update loading state
     * @private
     */
    _setLoading(isLoading) {
        if (isLoading) {
            this.activeRequests++;
        } else {
            this.activeRequests = Math.max(0, this.activeRequests - 1);
        }
        this.onLoadingChange(this.activeRequests > 0);
    }

    /**
     * Build full URL with query parameters
     * @private
     * @param {string} endpoint - API endpoint path (e.g., '/admin/settings')
     * @param {Object} [params] - Query parameters
     * @returns {string} Full URL
     */
    _buildURL(endpoint, params = {}) {
        // Build the full path by concatenating baseURL + endpoint
        // Remove leading slash from endpoint if present to avoid double slashes
        const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
        const fullPath = `${this.baseURL}/${cleanEndpoint}`;

        // Handle relative URLs by using window.location as base
        const baseUrl = this.baseURL.startsWith('http')
            ? this.baseURL
            : window.location.origin;

        // Create URL with full path
        const url = new URL(fullPath, window.location.origin);

        // Add query parameters
        Object.entries(params).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                url.searchParams.append(key, value);
            }
        });

        return url.toString();
    }

    /**
     * Get default headers
     * @private
     * @param {boolean} isFormData - Whether the request body is FormData
     * @returns {Headers}
     */
    _getHeaders(isFormData = false) {
        const headers = new Headers();
        // Don't set Content-Type for FormData - browser will set it with boundary
        if (!isFormData) {
            headers.append('Content-Type', 'application/json');
        }
        headers.append('Accept', 'application/json');
        headers.append('Accept-Language', this.getLocale());
        return headers;
    }

    /**
     * Make HTTP request
     * @private
     * @param {string} url - Full URL
     * @param {Object} options - Fetch options
     * @param {boolean} isFormData - Whether the request body is FormData
     * @returns {Promise<any>} Response data
     * @throws {ApiError}
     */
    /**
     * Make HTTP request
     * @private
     * @param {string} url - Full URL
     * @param {Object} options - Fetch options
     * @param {boolean} isFormData - Whether the request body is FormData
     * @returns {Promise<any>} Response data
     * @throws {ApiError}
     */
    async _request(url, options = {}, isFormData = false) {
        const skipGlobalLoading = options.skipGlobalLoading === true;
        if (!skipGlobalLoading) {
            this._setLoading(true);
        }

        try {
            // Extract custom fetch options, excluding client-specific options
            const { responseType = 'json', skipGlobalLoading: _, ...fetchOptions } = options;

            // Merge default headers with any custom headers
            const requestHeaders = this._getHeaders(isFormData);
            if (options.headers) {
                if (options.headers instanceof Headers) {
                    for (const [key, value] of options.headers.entries()) {
                        requestHeaders.set(key, value);
                    }
                } else {
                    Object.entries(options.headers).forEach(([key, value]) => {
                        requestHeaders.set(key, value);
                    });
                }
            }

            const response = await fetch(url, {
                ...fetchOptions,
                headers: requestHeaders
            });

            if (!response.ok) {
                throw await ApiError.fromResponse(response);
            }

            // Handle 204 No Content
            if (response.status === 204) {
                return null;
            }

            // Parse response based on requested responseType
            if (responseType === 'blob') {
                return await response.blob();
            }
            if (responseType === 'text') {
                return await response.text();
            }
            if (responseType === 'arraybuffer') {
                return await response.arrayBuffer();
            }

            return await response.json();
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }

            // Network error or other fetch failure
            throw ApiError.networkError(error);
        } finally {
            if (!skipGlobalLoading) {
                this._setLoading(false);
            }
        }
    }

    /**
     * GET request
     * @param {string} endpoint - API endpoint (e.g., '/borrowers/101')
     * @param {Object} [params] - Query parameters
     * @param {Object} [options] - Optional fetch options
     * @returns {Promise<any>}
     */
    async get(endpoint, params = {}, options = {}) {
        const url = this._buildURL(endpoint, params);
        return this._request(url, { method: 'GET', ...options });
    }

    /**
     * POST request
     * @param {string} endpoint - API endpoint
     * @param {Object|FormData} data - Request body (Object for JSON, FormData for file uploads)
     * @param {Object} [params] - Query parameters
     * @param {Object} [options] - Optional fetch options
     * @returns {Promise<any>}
     */
    async post(endpoint, data, params = {}, options = {}) {
        const url = this._buildURL(endpoint, params);
        const isFormData = data instanceof FormData;

        return this._request(url, {
            method: 'POST',
            body: isFormData ? data : JSON.stringify(data),
            ...options
        }, isFormData);
    }

    /**
     * PUT request
     * @param {string} endpoint - API endpoint
     * @param {Object|FormData} data - Request body (Object for JSON, FormData for file uploads)
     * @param {Object} [params] - Query parameters
     * @param {Object} [options] - Optional fetch options
     * @returns {Promise<any>}
     */
    async put(endpoint, data, params = {}, options = {}) {
        const url = this._buildURL(endpoint, params);
        const isFormData = data instanceof FormData;

        return this._request(url, {
            method: 'PUT',
            body: isFormData ? data : JSON.stringify(data),
            ...options
        }, isFormData);
    }

    /**
     * PATCH request
     * @param {string} endpoint - API endpoint
     * @param {Object|FormData} data - Request body (Object for JSON, FormData for file uploads)
     * @param {Object} [params] - Query parameters
     * @param {Object} [options] - Optional fetch options
     * @returns {Promise<any>}
     */
    async patch(endpoint, data, params = {}, options = {}) {
        const url = this._buildURL(endpoint, params);
        const isFormData = data instanceof FormData;

        return this._request(url, {
            method: 'PATCH',
            body: isFormData ? data : JSON.stringify(data),
            ...options
        }, isFormData);
    }

    /**
     * DELETE request
     * @param {string} endpoint - API endpoint
     * @param {Object} [data] - Optional request body
     * @param {Object} [params] - Query parameters
     * @param {Object} [options] - Optional fetch options
     * @returns {Promise<any>}
     */
    async delete(endpoint, data = null, params = {}, options = {}) {
        const url = this._buildURL(endpoint, params);
        const requestOptions = { method: 'DELETE', ...options };
        if (data !== null) {
            requestOptions.body = JSON.stringify(data);
        }
        return this._request(url, requestOptions);
    }
}

// Create singleton instance (will be configured in app.js)
export const apiClient = new ApiClient();
