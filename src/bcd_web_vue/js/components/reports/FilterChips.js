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
             style="background:#eef4ff;border:1px solid #c9d9f5;border-radius:8px;">
            <i class="bi bi-funnel-fill text-primary ms-1"></i>
            <span v-for="chip in chips" :key="chip.key"
                  class="badge d-inline-flex align-items-center gap-1"
                  style="background:#4D99F2;font-weight:500;font-size:12px;padding:4px 10px;border-radius:20px;">
                {{ chip.label }} : <strong>{{ chip.value }}</strong>
                <button
                    @click="$emit('clear', chip.key)"
                    style="background:rgba(255,255,255,.25);border:none;color:#fff;border-radius:50%;width:16px;height:16px;padding:0;font-size:11px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;"
                >×</button>
            </span>
            <button class="btn btn-sm btn-link text-danger p-0 ms-2" style="font-size:12px;" @click="$emit('clear-all')">
                {{ t('reports.clearAll') }}
            </button>
        </div>
    `
});
