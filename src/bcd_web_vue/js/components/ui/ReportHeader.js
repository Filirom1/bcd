/**
 * Reusable Report Header Component
 * Title + Print Button
 */

const { defineComponent } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'ReportHeader',

    props: {
        title: String,
        showNotices: { type: Boolean, default: false }
    },

    setup(props, { emit }) {
        const { t } = useI18n();

        const handlePrint = () => emit('print');

        return {
            t,
            handlePrint
        };
    },

    template: `
        <div class="page-header">
            <h1 class="page-title">
                <i class="bi bi-file-earmark-bar-graph me-2"></i>
                {{ title }}
            </h1>
            <div class="d-flex gap-2">
                <button v-if="showNotices" @click="$emit('print-notices')" class="btn btn-outline-primary">
                    <i class="bi bi-scissors me-2"></i>
                    {{ t('reports.overdue.printNotices') }}
                </button>
                <button @click="handlePrint" class="btn btn-primary">
                    <i class="bi bi-printer me-2"></i>
                    {{ t('reports.print') }}
                </button>
            </div>
        </div>
    `
});
