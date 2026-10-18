/**
 * Active filter chips row.
 * Displays a pill for each active cross-filter with an × to clear it.
 */

const { defineComponent } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'FilterChips',

    props: {
        chips: { type: Array, required: true },  // [{ key, label, value }]
    },

    emits: ['clear', 'clear-all'],

    setup() {
        const { t } = useI18n();
        return { t };
    },

    template: `
        <div v-if="chips.length"
             class="d-flex align-items-center gap-2 flex-wrap mb-2 px-2 py-2"
             style="background:var(--bcd-primary-subtle);border:1px solid var(--bcd-border);border-radius:var(--bcd-radius-md);">
            <i class="bi bi-funnel-fill text-primary ms-1"></i>
            <span v-for="chip in chips" :key="chip.key"
                  class="badge d-inline-flex align-items-center gap-1"
                  style="background:var(--bcd-primary);font-weight:500;font-size:var(--bcd-font-size-xs);padding:4px 10px;border-radius:var(--bcd-radius-sm);">
                {{ chip.label }} : <strong>{{ chip.value }}</strong>
                <button
                    @click="$emit('clear', chip.key)"
                    style="background:var(--bcd-white-overlay);border:none;color:var(--bcd-white);border-radius:50%;width:16px;height:16px;padding:0;font-size:var(--bcd-font-size-xs);cursor:pointer;display:inline-flex;align-items:center;justify-content:center;"
                >×</button>
            </span>
            <button class="btn btn-sm btn-link text-danger p-0 ms-2" style="font-size:var(--bcd-font-size-xs);" @click="$emit('clear-all')">
                {{ t('reports.clearAll') }}
            </button>
        </div>
    `
});
