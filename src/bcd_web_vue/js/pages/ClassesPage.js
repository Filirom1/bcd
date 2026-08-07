/**
 * Classes Page Component
 *
 * Main page for class management with CRUD operations.
 * Follows the same pattern as BorrowersPage.js.
 */

import ClassList from '../components/classes/ClassList.js';
import ClassForm from '../components/classes/ClassForm.js';
import ClassDeleteDialog from '../components/classes/ClassDeleteDialog.js';
import { useErrorHandler } from '../composables/useErrorHandler.js';
import { useNotification } from '../composables/useNotification.js';
import { useAdminShortcuts, altHeld } from '../composables/useKeyboardShortcuts.js';
import HelpPanel from '../components/ui/HelpPanel.js';
import { apiClient } from '../api/client.js';
import { events } from '../utils/events.js';

const { defineComponent, ref, onMounted, onBeforeUnmount } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'ClassesPage',

    components: {
        ClassList,
        ClassForm,
        ClassDeleteDialog,
        HelpPanel
    },

    template: `
        <div class="classes-page container-fluid">
            <!-- Page Header -->
            <div class="page-header">
                <div>
                    <h1 class="page-title">
                        <i class="bi bi-diagram-3 me-2"></i>
                        {{ t('admin.class_management') }}
                    </h1>
                    <p class="text-muted mb-0">{{ t('admin.class_management_subtitle', 'Manage school classes and grade levels') }}</p>
                </div>
                <div class="d-flex gap-2">
                    <button
                        type="button"
                        class="btn btn-primary"
                        @click="handleCreateClass"
                    >
                        <i class="bi bi-plus-circle me-1"></i>
                        {{ t('admin.create_class') }}
                        <kbd v-if="altHeld" class="admin-shortcut ms-2">N</kbd>
                        <kbd v-else class="admin-shortcut ms-2" style="visibility: hidden;">N</kbd>
                    </button>
                    <help-panel section="classes" />
                </div>
            </div>

            <!-- Results Summary -->
            <div v-if="!loading && classes.length > 0" class="mb-3">
                <div class="text-muted">
                    {{ t('admin.total_classes', { count: classes.length }, '{count} classes') }}
                </div>
            </div>

            <!-- Class List -->
            <class-list
                :classes="classes"
                :loading="loading"
                @edit-class="handleEditClass"
                @delete-class="handleDeleteClass"
            ></class-list>

            <!-- Class Form Modal -->
            <class-form
                :show="showFormModal"
                :class-data="selectedClass"
                @close="closeFormModal"
                @save="handleSaveClass"
            ></class-form>

            <!-- Delete Confirmation Dialog -->
            <class-delete-dialog
                v-if="classToDelete"
                :show="showDeleteDialog"
                :class-data="classToDelete"
                @close="closeDeleteDialog"
                @confirm="handleConfirmDelete"
            ></class-delete-dialog>
        </div>
    `,

    setup() {
        const { t } = useI18n();
        const { handleError } = useErrorHandler(t);
        const { success, error } = useNotification();

        // State
        const classes = ref([]);
        const loading = ref(false);
        const showFormModal = ref(false);
        const selectedClass = ref(null);
        const showDeleteDialog = ref(false);
        const classToDelete = ref(null);

        // Load classes from API
        const loadClasses = async () => {
            loading.value = true;

            try {
                classes.value = await apiClient.get('/classes', { limit: 500 });
            } catch (error) {
                handleError(error);
                classes.value = [];
            } finally {
                loading.value = false;
            }
        };

        // Handle create class
        const handleCreateClass = () => {
            selectedClass.value = null;
            showFormModal.value = true;
        };

        // Handle edit class
        const handleEditClass = (classObj) => {
            selectedClass.value = classObj;
            showFormModal.value = true;
        };

        // Handle save class (create or update)
        const handleSaveClass = async (formData) => {
            try {
                const payload = {
                    name: formData.name,
                    homeroom_teacher: formData.homeroom_teacher || null,
                    notes: formData.notes || null,
                    average_age: formData.average_age || null
                };

                if (formData.id) {
                    // Update existing class
                    await apiClient.patch(`/classes/${formData.id}`, payload);
                    success(t('admin.class_updated'));
                } else {
                    // Create new class
                    await apiClient.post('/classes', payload);
                    success(t('admin.class_created'));
                }

                // Reload classes and close modal
                await loadClasses();
                events.emit('classes:refresh');
                closeFormModal();

            } catch (error) {
                handleError(error);
            }
        };

        // Close form modal
        const closeFormModal = () => {
            showFormModal.value = false;
            selectedClass.value = null;
        };

        // Handle delete class
        const handleDeleteClass = (classObj) => {
            classToDelete.value = classObj;
            showDeleteDialog.value = true;
        };

        // Handle confirm delete
        const handleConfirmDelete = async (classId) => {
            try {
                await apiClient.delete(`/classes/${classId}`);

                success(t('admin.class_deleted'));

                // Reload classes and close dialog
                await loadClasses();
                events.emit('classes:refresh');
                closeDeleteDialog();

            } catch (error) {
                handleError(error);
            }
        };

        // Close delete dialog
        const closeDeleteDialog = () => {
            showDeleteDialog.value = false;
            classToDelete.value = null;
        };

        useAdminShortcuts({ N: handleCreateClass });

        // Load classes on mount and subscribe to refresh events
        const unsubscribe = events.on('classes:refresh', () => {
            loadClasses();
        });
        onBeforeUnmount(unsubscribe);

        // Load classes on mount
        onMounted(() => {
            loadClasses();
        });

        return {
            t,
            classes,
            loading,
            showFormModal,
            selectedClass,
            showDeleteDialog,
            classToDelete,
            handleCreateClass,
            handleEditClass,
            handleSaveClass,
            closeFormModal,
            handleDeleteClass,
            handleConfirmDelete,
            closeDeleteDialog,
            altHeld
        };
    }
});
