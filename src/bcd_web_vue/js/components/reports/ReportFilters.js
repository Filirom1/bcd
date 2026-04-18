/**
 * Reusable Report Filters Component
 * Configurable filters for different report types
 */

const { defineComponent, ref, onMounted } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';

export default defineComponent({
    name: 'ReportFilters',

    props: {
        showPeriod: Boolean,
        showLimit: Boolean,
        showClass: Boolean,
        showMediumType: Boolean,
        period: String,
        limit: Number,
        classFilter: String,
        mediumTypeFilter: { type: String, default: '' },
        mediumTypeOptions: { type: Array, default: () => [] }
    },

    emits: ['update:period', 'update:limit', 'update:classFilter', 'update:mediumTypeFilter', 'filter-change'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const classes = ref([]);

        const periodOptions = [
            { value: 'week', label: 'reports.period.week' },
            { value: 'month', label: 'reports.period.month' },
            { value: 'year', label: 'reports.period.year' },
            { value: 'all', label: 'reports.period.all' }
        ];

        const limitOptions = [10, 25, 50, 100];

        onMounted(async () => {
            if (props.showClass) await loadClasses();
        });

        const loadClasses = async () => {
            try {
                const response = await apiClient.get('/classes');
                // API returns array of class objects, extract just the names
                if (Array.isArray(response)) {
                    classes.value = response.map(cls => cls.name);
                } else if (response.classes) {
                    classes.value = response.classes;
                } else {
                    classes.value = [];
                }
            } catch (error) {
                console.error('Error loading classes:', error);
                classes.value = [];
            }
        };

        const updatePeriod = (value) => {
            emit('update:period', value);
            emit('filter-change');
        };

        const updateLimit = (value) => {
            emit('update:limit', parseInt(value));
            emit('filter-change');
        };

        const updateClass = (value) => {
            emit('update:classFilter', value);
            emit('filter-change');
        };

        const updateMediumType = (value) => {
            emit('update:mediumTypeFilter', value);
            emit('filter-change');
        };

        return {
            t,
            classes,
            periodOptions,
            limitOptions,
            updatePeriod,
            updateLimit,
            updateClass,
            updateMediumType
        };
    },

    template: `
        <div class="row g-3 mb-4">
            <!-- Period Filter -->
            <div v-if="showPeriod" class="col-md-3">
                <label class="form-label">{{ t('reports.period.label') }}</label>
                <select class="form-select" :value="period" @change="updatePeriod($event.target.value)">
                    <option v-for="opt in periodOptions" :key="opt.value" :value="opt.value">
                        {{ t(opt.label) }}
                    </option>
                </select>
            </div>

            <!-- Limit Filter -->
            <div v-if="showLimit" class="col-md-3">
                <label class="form-label">{{ t('reports.itemsPerPage') }}</label>
                <select class="form-select" :value="limit" @change="updateLimit($event.target.value)">
                    <option v-for="num in limitOptions" :key="num" :value="num">{{ num }}</option>
                </select>
            </div>

            <!-- Class Filter -->
            <div v-if="showClass" class="col-md-3">
                <label class="form-label">{{ t('reports.class') }}</label>
                <select class="form-select" :value="classFilter" @change="updateClass($event.target.value)">
                    <option value="">{{ t('reports.allClasses') }}</option>
                    <option v-for="cls in classes" :key="cls" :value="cls">{{ cls }}</option>
                </select>
            </div>

            <!-- Medium Type Filter -->
            <div v-if="showMediumType" class="col-md-3">
                <label class="form-label">{{ t('catalog.medium_type') }}</label>
                <select class="form-select" :value="mediumTypeFilter" @change="updateMediumType($event.target.value)">
                    <option value="">{{ t('common.all') }}</option>
                    <option v-for="mt in mediumTypeOptions" :key="mt" :value="mt">{{ mt }}</option>
                </select>
            </div>
        </div>
    `
});
