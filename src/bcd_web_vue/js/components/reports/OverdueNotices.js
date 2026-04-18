/**
 * Overdue Notices Print Page
 * Standalone page that loads overdue data and renders printable slips (2 per row, grouped by class).
 * Auto-triggers window.print() after data loads.
 */

const { defineComponent, ref, onMounted, nextTick } = Vue;
const { useI18n } = VueI18n;
import { apiClient } from '../../api/client.js';

export default defineComponent({
    name: 'OverdueNotices',

    setup() {
        const { t, d } = useI18n();
        const groupedData = ref({});
        const loading = ref(true);
        const error = ref(null);

        onMounted(async () => {
            try {
                const response = await apiClient.get('/reports/overdue', { limit: 500 });
                const items = response.data || response.items || response || [];
                // Group by class → then by borrower, so each slip covers one student's books
                const byClass = {};
                items.forEach(item => {
                    const cls = item.class_name || item.borrower_class || t('reports.overdue.noClass');
                    if (!byClass[cls]) byClass[cls] = {};
                    const bId = item.borrower_id;
                    if (!byClass[cls][bId]) {
                        byClass[cls][bId] = {
                            name: item.borrower_name,
                            class: cls,
                            books: []
                        };
                    }
                    byClass[cls][bId].books.push(item);
                });
                // Convert inner objects to arrays for v-for
                const groups = {};
                Object.keys(byClass).forEach(cls => {
                    groups[cls] = Object.values(byClass[cls]);
                });
                groupedData.value = groups;
                loading.value = false;
                await nextTick();
                window.print();
            } catch (err) {
                error.value = err.message || 'Erreur';
                loading.value = false;
            }
        });

        const doPrint = () => window.print();

        return { t, d, groupedData, loading, error, doPrint };
    },

    template: `
        <div>
            <div v-if="loading" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-2">{{ t('common.loading') }}</p>
            </div>

            <div v-else-if="error" class="alert alert-danger m-3">
                {{ error }}
            </div>

            <div v-else>
                <div class="notice-toolbar no-print">
                    <h2>{{ t('reports.overdue.noticesPageTitle') }}</h2>
                    <button @click="doPrint" class="btn btn-primary">
                        <i class="bi bi-printer me-2"></i>
                        {{ t('reports.print') }}
                    </button>
                </div>

                <div v-for="(borrowers, className) in groupedData" :key="className" class="notice-class-group">
                    <div class="notice-grid">
                        <div class="notice-class-title">{{ className }} — {{ borrowers.length }} {{ t('reports.overdue.borrower') }}</div>
                        <div v-for="borrower in borrowers" :key="borrower.name" class="notice-slip">
                            <div class="notice-slip-title">{{ t('reports.overdue.noticeTitle') }}</div>
                            <p><strong>{{ t('reports.overdue.noticeBorrower') }} :</strong> {{ borrower.name }} ({{ borrower.class }})</p>
                            <p class="notice-books-label"><strong>{{ t('reports.overdue.noticeBooks') }} :</strong></p>
                            <ul class="notice-book-list">
                                <li v-for="book in borrower.books" :key="book.item_id">
                                    « {{ book.title }} » (n°{{ book.item_id }}) —
                                    {{ t('reports.overdue.noticeBorrowedOn') }} : {{ d(new Date(book.checkout_date), 'short') }} —
                                    {{ t('reports.overdue.noticeDueOn') }} : {{ d(new Date(book.due_date), 'short') }}
                                    <span class="notice-overdue">— {{ t('reports.overdue.noticeOverdueBy', { days: book.days_overdue }) }}</span>
                                </li>
                            </ul>
                            <p class="notice-message">{{ t('reports.overdue.noticeMessage') }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `
});
