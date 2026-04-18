/**
 * Class List Component
 *
 * Table displaying classes with student count and action buttons.
 * Follows the same pattern as BorrowerList.js.
 */

const { computed } = Vue;
const { useI18n } = VueI18n;
import DataTable from '../ui/DataTable.js';

export default {
    name: 'ClassList',

    components: {
        DataTable
    },

    props: {
        classes: {
            type: Array,
            required: true
        },
        loading: {
            type: Boolean,
            default: false
        }
    },

    emits: ['edit-class', 'delete-class'],

    setup(props, { emit }) {
        const { t } = useI18n();

        // Define table columns
        const columns = computed(() => [
            { key: 'name', label: t('admin.class_name') },
            { key: 'homeroom_teacher', label: t('admin.homeroom_teacher') },
            { key: 'average_age', label: t('admin.average_age') },
            { key: 'student_count', label: t('admin.student_count') },
            { key: 'actions', label: t('common.actions') }
        ]);

        // Edit class
        const editClass = (classObj) => {
            emit('edit-class', classObj);
        };

        // Delete class
        const deleteClass = (classObj) => {
            emit('delete-class', classObj);
        };

        return {
            t,
            columns,
            editClass,
            deleteClass
        };
    },

    template: `
        <data-table
            :columns="columns"
            :rows="classes"
            :loading="loading"
            :empty-message="t('admin.no_classes')"
            row-key="id"
        >
            <template #row="{ row: classObj }">
                <!-- Class Name -->
                <td>
                    <span class="fw-bold">{{ classObj.name }}</span>
                </td>

                <!-- Homeroom Teacher -->
                <td>
                    <span v-if="classObj.homeroom_teacher">{{ classObj.homeroom_teacher }}</span>
                    <span v-else class="text-muted">—</span>
                </td>

                <!-- Average Age -->
                <td>
                    <span v-if="classObj.average_age !== null && classObj.average_age !== undefined">
                        {{ classObj.average_age }}
                    </span>
                    <span v-else class="text-muted">—</span>
                </td>

                <!-- Student Count -->
                <td>
                    <span class="badge bg-info text-dark">
                        {{ classObj.student_count }}
                    </span>
                </td>

                <!-- Actions -->
                <td>
                    <button
                        type="button"
                        class="btn btn-sm btn-outline-primary me-1"
                        @click.stop="editClass(classObj)"
                        :title="t('admin.edit_class')"
                    >
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button
                        type="button"
                        class="btn btn-sm btn-outline-danger"
                        @click.stop="deleteClass(classObj)"
                        :title="t('admin.delete_class')"
                    >
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </template>
        </data-table>
    `
};
