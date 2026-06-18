const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
const { useRoute } = VueRouter;
import { useBarcodeRenderer } from '../composables/useBarcodeRenderer.js';
import { useBorrowerData } from '../composables/useBorrowerData.js';

export default defineComponent({
    name: 'PrintBorrowerReference',

    setup() {
        const { t } = useI18n();
        const route = useRoute();
        const { renderBarcodes } = useBarcodeRenderer();
        const { fetchBorrowers, fetchSettings } = useBorrowerData();

        const borrowers = ref([]);
        const settings = ref(null);
        const loading = ref(true);
        const error = ref(null);

        const totalCount = computed(() => borrowers.value.length);

        // Add prefix to borrower barcodes for printing
        const borrowersWithPrefixedBarcodes = computed(() => {
            const prefix = settings.value?.borrower_barcode_prefix ?? '';
            return borrowers.value.map(b => ({
                ...b,
                barcodeWithPrefix: `${prefix}${b.barcode}`
            }));
        });

        // Group borrowers with prefixed barcodes by class_name
        const borrowersByClassWithPrefix = computed(() => {
            const grouped = {};
            borrowersWithPrefixedBarcodes.value.forEach(b => {
                const className = b.class_name || 'Sans classe';
                if (!grouped[className]) {
                    grouped[className] = {
                        students: [],
                        homeroom_teacher: b.homeroom_teacher || null
                    };
                }
                grouped[className].students.push(b);
            });

            // Sort students within each class by last_name, then first_name
            for (const className in grouped) {
                grouped[className].students.sort((a, b) =>
                    (a.last_name || '').localeCompare(b.last_name || '') ||
                    (a.first_name || '').localeCompare(b.first_name || '')
                );
            }

            // Return sorted by class name
            return Object.fromEntries(
                Object.entries(grouped).sort(([a], [b]) => a.localeCompare(b))
            );
        });

        onMounted(async () => {
            try {
                // Fetch borrowers and settings in parallel
                const classIds = route.query.class_ids;
                const [borrowerData, settingsData] = await Promise.all([
                    fetchBorrowers(classIds),
                    fetchSettings()
                ]);

                borrowers.value = borrowerData;
                settings.value = settingsData;
                loading.value = false;

                // Render barcodes after DOM updates
                await nextTick();
                const format = (settings.value?.barcode_type || 'code39').toUpperCase();
                renderBarcodes({
                    format: format,
                    width: 2,
                    height: 50
                });
            } catch (err) {
                error.value = err.message;
                loading.value = false;
            }
        });

        const printPage = () => window.print();

        return { t, borrowersByClass: borrowersByClassWithPrefix, loading, error, totalCount, printPage };
    },

    template: `
        <div class="print-page">
            <!-- Toolbar (hidden when printing) -->
            <div class="print-toolbar no-print">
                <h1 class="page-title">
                    <i class="bi bi-card-list me-2"></i>
                    {{ t('admin.print_borrower_reference') }}
                </h1>
                <div>
                    <span class="text-muted me-3">{{ totalCount }} borrowers</span>
                    <button class="btn btn-primary" @click="printPage">
                        <i class="bi bi-printer me-1"></i>
                        {{ t('reports.print') }}
                    </button>
                </div>
            </div>

            <!-- Loading state -->
            <div v-if="loading" class="text-center p-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-3 text-muted">{{ t('common.loading') }}</p>
            </div>

            <!-- Error state -->
            <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

            <!-- Content: students grouped by class -->
            <div v-else>
                <div
                    v-for="(classData, className) in borrowersByClass"
                    :key="className"
                    class="class-section"
                >
                    <h1 class="class-header">{{ className }}</h1>
                    <p v-if="classData.homeroom_teacher" class="homeroom-teacher">
                        {{ t('admin.homeroom_teacher') }}: {{ classData.homeroom_teacher }}
                    </p>

                    <div
                        v-for="student in classData.students"
                        :key="student.id"
                        class="borrower-row"
                    >
                        <div class="borrower-id">{{ student.borrower_id }}</div>
                        <div class="borrower-barcode">
                            <svg class="barcode" :data-code="student.barcodeWithPrefix"></svg>
                        </div>
                        <div class="borrower-name">
                            {{ student.last_name }} {{ student.first_name }}
                        </div>
                        <div class="borrower-status">
                            {{ student.role === 'student' ? 'Eleve' : student.role }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
});
