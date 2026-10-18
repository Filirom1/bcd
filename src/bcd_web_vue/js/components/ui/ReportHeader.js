/**
 * Reusable Report Header Component
 * Title + Print Button
 */

const { defineComponent } = Vue;
const { useI18n } = VueI18n;
import HelpPanel from './HelpPanel.js';
import PageHeader from './PageHeader.js';

export default defineComponent({
    name: 'ReportHeader',

    components: { HelpPanel, PageHeader },

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
        <page-header>
            <template #heading>
                <h1 class="page-title">
                    <i class="bi bi-file-earmark-bar-graph me-2"></i>
                    {{ title }}
                </h1>
            </template>
            <template #actions>
                <div class="d-flex gap-2">
                    <button v-if="showNotices" @click="$emit('print-notices')" class="btn btn-outline-primary">
                        <i class="bi bi-scissors me-2"></i>
                        {{ t('reports.overdue.printNotices') }}
                    </button>
                    <button @click="handlePrint" class="btn btn-primary">
                        <i class="bi bi-printer me-2"></i>
                        {{ t('reports.print') }}
                    </button>
                    <help-panel section="reports" />
                </div>
            </template>
        </page-header>
    `
});
