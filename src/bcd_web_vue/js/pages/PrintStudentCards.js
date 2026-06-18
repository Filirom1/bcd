const { defineComponent, ref, computed, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
const { useRoute } = VueRouter;
import { useBarcodeRenderer } from '../composables/useBarcodeRenderer.js';
import { useBorrowerData } from '../composables/useBorrowerData.js';

export default defineComponent({
    name: 'PrintStudentCards',

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

                // Render barcodes after DOM update
                await nextTick();
                const format = (settings.value?.barcode_type || 'code39').toUpperCase();
                renderBarcodes({
                    format: format,
                    width: 2.5,
                    height: 50
                });
            } catch (err) {
                error.value = err.message;
                loading.value = false;
            }
        });

        const libraryName = computed(() =>
            settings.value?.library_name || ''
        );

        const printPage = () => window.print();

        return { t, borrowers: borrowersWithPrefixedBarcodes, loading, error, totalCount, libraryName, printPage };
    },

    template: `
        <div class="print-page">
            <!-- Toolbar (hidden when printing) -->
            <div class="print-toolbar no-print">
                <h1 class="page-title">
                    <i class="bi bi-person-badge me-2"></i>
                    {{ t('admin.print_student_cards') }}
                </h1>
                <div>
                    <span class="text-muted me-3">{{ totalCount }} cards</span>
                    <button class="btn btn-primary" @click="printPage">
                        <i class="bi bi-printer me-1"></i>
                        {{ t('reports.print') }}
                    </button>
                </div>
            </div>

            <!-- Loading -->
            <div v-if="loading" class="text-center p-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-3 text-muted">{{ t('common.loading') }}</p>
            </div>

            <!-- Error -->
            <div v-else-if="error" class="alert alert-danger">{{ error }}</div>

            <!-- Card Grid: 2 columns x 5 rows = 10 cards per A4 page -->
            <div v-else class="card-grid">
                <div
                    v-for="student in borrowers"
                    :key="student.id"
                    class="library-card"
                >
                    <div class="card-header">
                        {{ libraryName }}
                        <span v-if="student.class_name"> - {{ student.class_name }}</span>
                    </div>

                    <div class="card-body">
                        <div class="card-info">
                            <div class="card-name">
                                {{ student.last_name }} {{ student.first_name }}
                            </div>
                            <div class="card-id">{{ student.borrower_id }}</div>
                            <div class="card-role">
                                {{ student.role === 'student' ? 'Eleve' : student.role }}
                            </div>
                        </div>
                    </div>

                    <div class="card-barcode">
                        <svg class="barcode" :data-code="student.barcodeWithPrefix"></svg>
                    </div>
                </div>
            </div>
        </div>
    `
});
