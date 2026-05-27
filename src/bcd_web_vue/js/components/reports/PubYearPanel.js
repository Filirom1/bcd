/**
 * Publication year histogram + dual range slider.
 * Colors by age: red >10 years, orange 5-10 years, blue <5 years.
 */

const { defineComponent, computed, ref, watch } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'PubYearPanel',

    props: {
        items:    { type: Array,  required: true },  // items with .publication_year
        modelMin: { type: Number, default: null },
        modelMax: { type: Number, default: null },
    },

    emits: ['update:modelMin', 'update:modelMax'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const curYear = new Date().getFullYear();

        const histogram = computed(() => {
            const counts = {};
            props.items.forEach(item => {
                const yr = item.publication_year;
                if (yr) counts[yr] = (counts[yr] || 0) + 1;
            });
            if (!Object.keys(counts).length) return [];
            const years = Object.keys(counts).map(Number).sort((a, b) => a - b);
            const result = [];
            for (let y = years[0]; y <= years[years.length - 1]; y++) {
                result.push({ bin: y, count: counts[y] || 0 });
            }
            return result;
        });

        const dataRange = computed(() => {
            if (!histogram.value.length) return { min: curYear - 10, max: curYear };
            return { min: histogram.value[0].bin, max: histogram.value[histogram.value.length - 1].bin };
        });

        const maxCount = computed(() => Math.max(...histogram.value.map(b => b.count), 1));

        const sliderMin = ref(dataRange.value.min);
        const sliderMax = ref(dataRange.value.max);

        watch(() => props.modelMin, val => { sliderMin.value = val ?? dataRange.value.min; });
        watch(() => props.modelMax, val => { sliderMax.value = val ?? dataRange.value.max; });
        watch(dataRange, r => {
            if (props.modelMin === null) sliderMin.value = r.min;
            if (props.modelMax === null) sliderMax.value = r.max;
        });

        const clampMin = () => { if (sliderMin.value >= sliderMax.value) sliderMin.value = sliderMax.value - 1; };
        const clampMax = () => { if (sliderMax.value <= sliderMin.value) sliderMax.value = sliderMin.value + 1; };

        const applyRange = () => {
            const r = dataRange.value;
            const atDefault = sliderMin.value === r.min && sliderMax.value === r.max;
            emit('update:modelMin', atDefault ? null : sliderMin.value);
            emit('update:modelMax', atDefault ? null : sliderMax.value);
        };

        const isInRange = bin => {
            if (props.modelMin === null && props.modelMax === null) return true;
            if (props.modelMin !== null && bin < props.modelMin) return false;
            if (props.modelMax !== null && bin > props.modelMax) return false;
            return true;
        };

        const fillStyle = computed(() => {
            const { min, max } = dataRange.value;
            const total = max - min;
            if (total <= 0) return {};
            const left  = (sliderMin.value - min) / total * 100;
            const right = (max - sliderMax.value) / total * 100;
            return { left: left + '%', right: right + '%' };
        });

        const barColor = bin => {
            const age = curYear - bin;
            return age > 10 ? '#F24D66' : age > 5 ? '#F2BF33' : '#4D99F2';
        };

        return { t, histogram, dataRange, maxCount, sliderMin, sliderMax, clampMin, clampMax, applyRange, isInRange, fillStyle, barColor };
    },

    template: `
        <div class="card h-100">
            <div class="card-body p-3">
                <div class="text-uppercase fw-bold mb-2" style="font-size:11px;letter-spacing:.8px;color:#6c757d;">
                    {{ t('reports.pubYear.label') }}
                </div>

                <div v-if="!histogram.length" class="text-muted small">—</div>

                <!-- CSS histogram -->
                <div v-if="histogram.length" class="d-flex mb-2" style="height:80px;align-items:flex-end;gap:1px;">
                    <div v-for="b in histogram" :key="b.bin"
                         style="flex:1;height:80px;display:flex;flex-direction:column;justify-content:flex-end;min-width:2px;"
                         :title="b.bin + ': ' + b.count">
                        <div :style="{
                            height: (b.count / maxCount * 100) + '%',
                            background: barColor(b.bin),
                            borderRadius: '2px 2px 0 0',
                            opacity: isInRange(b.bin) ? 1 : 0.25,
                            transition: 'opacity 0.2s'
                        }"></div>
                    </div>
                </div>

                <!-- Dual range slider -->
                <div class="range-slider-container" v-if="histogram.length">
                    <div class="range-slider-track"></div>
                    <div class="range-slider-fill" :style="fillStyle"></div>
                    <input type="range" class="dual-range-input"
                           :min="dataRange.min" :max="dataRange.max" step="1"
                           v-model.number="sliderMin"
                           @input="clampMin" @change="applyRange">
                    <input type="range" class="dual-range-input"
                           :min="dataRange.min" :max="dataRange.max" step="1"
                           v-model.number="sliderMax"
                           @input="clampMax" @change="applyRange">
                </div>
                <div class="d-flex justify-content-between" style="font-size:11px;color:#888;margin-top:2px;">
                    <span>{{ sliderMin }}</span>
                    <span>{{ sliderMax }}</span>
                </div>

                <!-- Legend -->
                <div class="mt-1" style="font-size:11px;color:#aaa;">
                    <i class="bi bi-square-fill text-danger me-1"></i>{{ t('reports.pubYear.ageOld') }} &nbsp;
                    <i class="bi bi-square-fill text-warning me-1"></i>{{ t('reports.pubYear.ageMid') }} &nbsp;
                    <i class="bi bi-square-fill me-1" style="color:#4D99F2;"></i>{{ t('reports.pubYear.ageNew') }}
                </div>
            </div>
        </div>
    `
});
