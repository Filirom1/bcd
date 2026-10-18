/**
 * Reusable breakdown bar panel for reports.
 * Displays a ranked list of values with proportional bars.
 * Clicking a row toggles a cross-filter.
 */

const { defineComponent, computed } = Vue;

export default defineComponent({
    name: 'BreakdownPanel',

    props: {
        title:       { type: String,   required: true },
        subtitle:    { type: String,   default: '' },
        rows:        { type: Array,    required: true },  // [{ value, count }]
        activeValue: { type: String,   default: null },
        colors:      { type: Array,    default: () => [
            'var(--bcd-chart-1)', 'var(--bcd-chart-2)', 'var(--bcd-chart-3)',
            'var(--bcd-chart-4)', 'var(--bcd-chart-5)', 'var(--bcd-chart-6)',
            'var(--bcd-chart-muted)'
        ] },
        labelFn:     { type: Function, default: null },
        colorFn:     { type: Function, default: null },   // (row, index) => color string
    },

    emits: ['toggle'],

    setup(props) {
        const max = computed(() => Math.max(...props.rows.map(r => r.count), 1));
        const label = val => props.labelFn ? props.labelFn(val) : val;
        const color = (row, i) => props.colorFn ? props.colorFn(row, i) : props.colors[i % props.colors.length];
        return { max, label, color };
    },

    template: `
        <div class="card h-100">
            <div class="card-body p-3">
                <div class="text-uppercase fw-bold mb-2" style="font-size:var(--bcd-font-size-xs);letter-spacing:.8px;color:var(--bcd-text-muted);">
                    {{ title }}
                    <span v-if="subtitle" class="fw-normal text-muted ms-1" style="text-transform:none;letter-spacing:0;">· {{ subtitle }}</span>
                </div>
                <div v-if="!rows.length" class="text-muted small">—</div>
                <div
                    v-for="(row, i) in rows" :key="row.value"
                    @click="$emit('toggle', row.value)"
                    class="d-flex align-items-center gap-2 mb-1 px-1 py-1 rounded"
                    style="cursor:pointer;"
                    :style="activeValue === row.value ? 'background:var(--bcd-selection);outline:2px solid var(--bcd-primary);' : ''"
                >
                    <span style="min-width:90px;font-size:var(--bcd-font-size-xs);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" :title="row.value">
                        {{ label(row.value) }}
                    </span>
                    <div style="flex:1;background:var(--bcd-chart-track);border-radius:var(--bcd-radius-sm);height:7px;overflow:hidden;">
                        <div :style="{ width: Math.round(row.count / max * 100) + '%', background: color(row, i), height: '100%', borderRadius: 'var(--bcd-radius-sm)' }"></div>
                    </div>
                    <span style="min-width:28px;font-size:var(--bcd-font-size-xs);font-weight:600;text-align:right;">{{ row.count }}</span>
                </div>
            </div>
        </div>
    `
});
