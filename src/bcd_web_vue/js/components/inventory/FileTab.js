/**
 * FileTab Component
 * File upload and parsing for inventory barcode import
 */

const { defineComponent, ref, computed } = Vue;
const { useI18n } = VueI18n;

import { useNotification } from '../../composables/useNotification.js';
import { useErrorHandler } from '../../composables/useErrorHandler.js';

export default defineComponent({
    name: 'FileTab',

    props: {
        inventoryTable: {
            type: Object,
            required: true
        }
    },

    emits: ['switch-to-working-table'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const { success, error: showError } = useNotification();
        const { handleError } = useErrorHandler(t);

        const fileInput = ref(null);
        const fileName = ref('');
        const parsing = ref(false);
        const importing = ref(false);
        const parseResult = ref(null);

        /**
         * Parse file contents into item IDs
         */
        const parseFile = (content) => {
            // Split by newlines
            const lines = content.split(/\r?\n/);

            // Process each line
            const itemIds = lines
                .map(line => line.trim())
                .filter(line => line.length > 0 && !line.startsWith('#')) // Remove blanks and comments
                .map(line => {
                    // Strip barcode prefix if present (e.g., ".0785" -> "0785")
                    return line.startsWith('.') ? line.substring(1) : line;
                });

            // Deduplicate
            return [...new Set(itemIds)];
        };

        /**
         * Handle file selection
         */
        const handleFileChange = async (event) => {
            const file = event.target.files[0];
            if (!file) {
                return;
            }

            fileName.value = file.name;
            parsing.value = true;
            parseResult.value = null;

            try {
                // Read file contents
                const content = await file.text();

                // Parse item IDs
                const itemIds = parseFile(content);

                if (itemIds.length === 0) {
                    showError(t('inventory.file.no_valid_ids'));
                    parsing.value = false;
                    return;
                }

                // Call backend to validate which IDs exist
                const response = await fetch('/api/v1/inventory/items/bulk-mark', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        item_ids: itemIds
                    })
                });

                if (!response.ok) {
                    throw new Error(await response.text());
                }

                const data = await response.json();

                // Store parse result
                parseResult.value = {
                    totalIds: itemIds, // Store the actual array, not the length
                    totalCount: itemIds.length,
                    validCount: data.items_updated,
                    unknownIds: data.items_not_found || [],
                    timestamp: data.timestamp
                };

                parsing.value = false;
            } catch (error) {
                handleError(error, 'inventory.file.error');
                parsing.value = false;
            }
        };

        /**
         * Import valid items to working table
         */
        const handleImport = async () => {
            if (!parseResult.value || parseResult.value.validCount === 0) {
                return;
            }

            importing.value = true;

            try {
                // Fetch all valid items and add to working table
                // The items were already marked as inventoried by the validation call
                // Now we need to fetch their full details
                const allItemIds = parseResult.value.totalIds;
                const unknownSet = new Set(parseResult.value.unknownIds);
                const validIds = allItemIds.filter(id => !unknownSet.has(id));

                // Fetch item details in batches
                const batchSize = 50;
                for (let i = 0; i < validIds.length; i += batchSize) {
                    const batch = validIds.slice(i, i + batchSize);

                    await Promise.all(
                        batch.map(async (itemId) => {
                            try {
                                const response = await fetch(`/api/v1/inventory/items/${itemId}`, {
                                    method: 'PATCH'
                                });
                                if (response.ok) {
                                    const item = await response.json();
                                    props.inventoryTable.addItem(item);
                                }
                            } catch (err) {
                                console.error(`Failed to fetch item ${itemId}:`, err);
                            }
                        })
                    );
                }

                success(t('inventory.file.import_success', { count: validIds.length }));

                // Reset file input
                if (fileInput.value) {
                    fileInput.value.value = '';
                }
                fileName.value = '';
                parseResult.value = null;

                // Switch to working table to show imported items
                emit('switch-to-working-table');
            } catch (error) {
                handleError(error, 'inventory.file.error');
            } finally {
                importing.value = false;
            }
        };

        /**
         * Clear file selection
         */
        const handleClear = () => {
            if (fileInput.value) {
                fileInput.value.value = '';
            }
            fileName.value = '';
            parseResult.value = null;
        };

        const showUnknownIds = ref(false);

        return {
            t,
            fileInput,
            fileName,
            parsing,
            importing,
            parseResult,
            handleFileChange,
            handleImport,
            handleClear,
            showUnknownIds
        };
    },

    template: `
        <div class="file-tab">
            <!-- Help text -->
            <p class="text-muted small mb-3">
                {{ t('inventory.file.file_format') }}
            </p>

            <!-- File input -->
            <div class="mb-3">
                <input
                    ref="fileInput"
                    type="file"
                    class="form-control"
                    accept=".txt"
                    @change="handleFileChange"
                />
            </div>

            <!-- Parsing status -->
            <div v-if="parsing" class="alert alert-info">
                <span class="spinner-border spinner-border-sm me-2"></span>
                {{ t('inventory.file.parsing') }}
            </div>

            <!-- Parse results -->
            <div v-if="parseResult" class="parse-results">
                <div class="alert alert-success mb-3">
                    <div class="mb-2">
                        <strong>{{ t('inventory.file.ids_found', { count: parseResult.totalCount }) }}</strong>
                    </div>
                    <div class="mb-1">
                        <span class="badge bg-success me-2">
                            {{ t('inventory.file.valid_count', { count: parseResult.validCount }) }}
                        </span>
                        <span v-if="parseResult.unknownIds.length > 0" class="badge bg-warning">
                            {{ t('inventory.file.unknown_count', { count: parseResult.unknownIds.length }) }}
                        </span>
                    </div>

                    <!-- Unknown IDs toggle -->
                    <div v-if="parseResult.unknownIds.length > 0" class="mt-2">
                        <button
                            type="button"
                            class="btn btn-sm btn-outline-secondary"
                            @click="showUnknownIds = !showUnknownIds"
                        >
                            <i class="bi" :class="showUnknownIds ? 'bi-chevron-up' : 'bi-chevron-down'"></i>
                            {{ t('inventory.file.view_errors') }}
                        </button>

                        <!-- Unknown IDs list -->
                        <div v-if="showUnknownIds" class="mt-2 p-2 bg-light rounded" style="max-height: 200px; overflow-y: auto;">
                            <ul class="list-unstyled mb-0 small">
                                <li v-for="id in parseResult.unknownIds" :key="id" class="text-muted">
                                    {{ id }}
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>

                <!-- Action buttons -->
                <div class="d-flex gap-2">
                    <button
                        type="button"
                        class="btn btn-primary"
                        :disabled="parseResult.validCount === 0 || importing"
                        @click="handleImport"
                    >
                        <span v-if="importing" class="spinner-border spinner-border-sm me-2"></span>
                        {{ t('inventory.file.import_button', { count: parseResult.validCount }) }}
                    </button>
                    <button
                        type="button"
                        class="btn btn-secondary"
                        :disabled="importing"
                        @click="handleClear"
                    >
                        {{ t('common.clear') }}
                    </button>
                </div>
            </div>

            <!-- No valid IDs warning -->
            <div v-if="parseResult && parseResult.validCount === 0" class="alert alert-warning">
                {{ t('inventory.file.no_valid_ids') }}
            </div>
        </div>
    `
});
