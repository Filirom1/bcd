/**
 * AdminDropdown Component
 *
 * Reusable red "Admin" dropdown button for Borrower & Catalog pages.
 * Groups destructive/sensitive operations (import, export, bulk edit, edit selected).
 *
 * Props:
 * - selectedCount (Number): Number of items currently selected
 * - page (String): Current page context ('borrowers' or 'catalog')
 *
 * Emits:
 * - import: User clicked Import menu item
 * - export: User clicked Export menu item
 * - bulk-edit: User clicked Bulk Edit menu item (enabled when selectedCount >= 1)
 * - edit-selected: User clicked Edit Selected menu item (enabled when selectedCount === 1)
 */

const { defineComponent, computed } = Vue;
const { useI18n } = VueI18n;
import { useAdminShortcuts, altHeld } from '../../composables/useKeyboardShortcuts.js';

export default defineComponent({
    name: 'AdminDropdown',

    props: {
        selectedCount: {
            type: Number,
            default: 0
        },
        page: {
            type: String,
            required: true,
            validator: (value) => ['borrowers', 'catalog', 'inventory'].includes(value)
        }
    },

    emits: ['import', 'export', 'bulk-edit', 'edit-selected', 'print-reference', 'print-cards', 'print-labels', 'cleanup-orphans'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Conditional enabling logic
        const isBulkEditEnabled = computed(() => props.selectedCount >= 2);
        const isEditSelectedEnabled = computed(() => props.selectedCount === 1);

        // Import/Export labels based on page context
        const importLabel = computed(() => {
            if (props.page === 'borrowers') {
                return t('admin.import_borrowers');
            } else if (props.page === 'inventory') {
                return t('admin.import_inventory');
            } else {
                return t('admin.import_catalog');
            }
        });

        const exportLabel = computed(() => {
            if (props.page === 'borrowers') {
                return t('admin.export_borrowers');
            } else if (props.page === 'inventory') {
                return t('admin.export_inventory');
            } else {
                return t('admin.export_catalog');
            }
        });

        // Event handlers
        const handleImport = () => {
            emit('import');
        };

        const handleExport = () => {
            emit('export');
        };

        const handleBulkEdit = () => {
            if (isBulkEditEnabled.value) {
                emit('bulk-edit');
            }
        };

        const handleEditSelected = () => {
            if (isEditSelectedEnabled.value) {
                emit('edit-selected');
            }
        };

        // Print handlers (page-contextual)
        const handlePrint = () => {
            if (props.page === 'borrowers') {
                emit('print-reference');
            } else {
                emit('print-labels');
            }
        };

        const handlePrintCards = () => {
            if (props.page === 'borrowers') {
                emit('print-cards');
            }
        };

        // Register Alt+Letter shortcuts for this page
        useAdminShortcuts({
            I: handleImport,
            X: handleExport,
            E: handleEditSelected,
            M: handleBulkEdit,
            P: handlePrint,
            K: handlePrintCards,
        });

        return {
            t,
            importLabel,
            exportLabel,
            isBulkEditEnabled,
            isEditSelectedEnabled,
            handleImport,
            handleExport,
            handleBulkEdit,
            handleEditSelected,
            altHeld
        };
    },

    template: `
        <div class="dropdown">
            <button
                class="btn btn-danger dropdown-toggle"
                type="button"
                id="adminDropdown"
                data-bs-toggle="dropdown"
                data-testid="admin-dropdown-button"
                aria-expanded="false"
            >
                <i class="bi bi-shield-lock"></i>
                {{ t('admin.menu_title') }}
            </button>
            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="adminDropdown">
                <!-- Import -->
                <li>
                    <a
                        class="dropdown-item d-flex align-items-center"
                        href="#"
                        data-testid="admin-menu-import"
                        @click.prevent="handleImport"
                    >
                        <i class="bi bi-upload me-2"></i>
                        <span class="flex-grow-1">{{ importLabel }}</span>
                        <kbd v-if="altHeld" class="admin-shortcut ms-2">I</kbd>
                    </a>
                </li>

                <!-- Export -->
                <li>
                    <a
                        class="dropdown-item d-flex align-items-center"
                        href="#"
                        data-testid="admin-menu-export"
                        @click.prevent="handleExport"
                    >
                        <i class="bi bi-download me-2"></i>
                        <span class="flex-grow-1">{{ exportLabel }}</span>
                        <kbd v-if="altHeld" class="admin-shortcut ms-2">X</kbd>
                    </a>
                </li>

                <!-- Edit/Bulk operations (only for borrowers and catalog) -->
                <template v-if="page !== 'inventory'">
                    <!-- Divider -->
                    <li><hr class="dropdown-divider"></li>

                    <!-- Edit Selected (enabled only when selectedCount === 1) -->
                    <li>
                        <a
                            class="dropdown-item d-flex align-items-center"
                            :class="{ 'disabled': !isEditSelectedEnabled }"
                            href="#"
                            data-testid="admin-menu-edit-selected"
                            @click.prevent="handleEditSelected"
                        >
                            <i class="bi bi-pencil-square me-2"></i>
                            <span class="flex-grow-1">
                                {{ t('admin.edit_selected') }}
                                <span v-if="!isEditSelectedEnabled" class="text-muted small">
                                    ({{ t('admin.select_exactly_one') }})
                                </span>
                            </span>
                            <kbd v-if="altHeld" class="admin-shortcut ms-2">E</kbd>
                        </a>
                    </li>

                    <!-- Bulk Edit (enabled when selectedCount >= 2) -->
                    <li>
                        <a
                            class="dropdown-item d-flex align-items-center"
                            :class="{ 'disabled': !isBulkEditEnabled }"
                            href="#"
                            data-testid="admin-menu-bulk-edit"
                            @click.prevent="handleBulkEdit"
                        >
                            <i class="bi bi-pencil me-2"></i>
                            <span class="flex-grow-1">
                                {{ t('admin.bulk_edit') }}
                                <span v-if="!isBulkEditEnabled" class="text-muted small">
                                    ({{ t('admin.select_at_least_two', 'Select at least 2') }})
                                </span>
                            </span>
                            <kbd v-if="altHeld" class="admin-shortcut ms-2">M</kbd>
                        </a>
                    </li>

                    <!-- Print Divider -->
                    <li><hr class="dropdown-divider"></li>
                </template>

                <!-- Cleanup orphans (only for inventory) -->
                <template v-if="page === 'inventory'">
                    <!-- Divider -->
                    <li><hr class="dropdown-divider"></li>

                    <li>
                        <a
                            class="dropdown-item d-flex align-items-center"
                            href="#"
                            @click.prevent="$emit('cleanup-orphans')"
                        >
                            <i class="bi bi-trash me-2"></i>
                            <span class="flex-grow-1">{{ t('admin.cleanup_orphans') }}</span>
                        </a>
                    </li>
                </template>

                <!-- Print options for Borrowers page -->
                <template v-if="page === 'borrowers'">
                    <li>
                        <a
                            class="dropdown-item d-flex align-items-center"
                            href="#"
                            @click.prevent="$emit('print-reference')"
                        >
                            <i class="bi bi-file-text me-2"></i>
                            <span class="flex-grow-1">{{ t('admin.print_borrower_reference') }}</span>
                            <kbd v-if="altHeld" class="admin-shortcut ms-2">P</kbd>
                        </a>
                    </li>
                    <li>
                        <a
                            class="dropdown-item d-flex align-items-center"
                            href="#"
                            @click.prevent="$emit('print-cards')"
                        >
                            <i class="bi bi-credit-card me-2"></i>
                            <span class="flex-grow-1">{{ t('admin.print_student_cards') }}</span>
                            <kbd v-if="altHeld" class="admin-shortcut ms-2">K</kbd>
                        </a>
                    </li>
                </template>

                <!-- Print options for Catalog page -->
                <template v-if="page === 'catalog'">
                    <li>
                        <a
                            class="dropdown-item d-flex align-items-center"
                            href="#"
                            @click.prevent="$emit('print-labels')"
                        >
                            <i class="bi bi-printer me-2"></i>
                            <span class="flex-grow-1">{{ t('admin.print_item_labels') }}</span>
                            <kbd v-if="altHeld" class="admin-shortcut ms-2">P</kbd>
                        </a>
                    </li>
                </template>
            </ul>
        </div>
    `
});
