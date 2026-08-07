/**
 * DeweyPicker Component
 *
 * Call number input with a 2-level Dewey classification assistant.
 * - Colored badge (live, derived from first digit of call number)
 * - Toggle button opens a picker: 10 class buttons → 10 subdivision buttons
 * - Clicking a subdivision inserts the 3-digit code into the field
 * - Colors come from settings.dewey_colors (array of 10 hex strings)
 * - Labels come from vue-i18n (dewey.class.N, dewey.class_full.N, dewey.sub.NNN)
 *
 * Usage:
 *   <dewey-picker v-model="callNumber" :colors="deweyColors" :placeholder="..." />
 */

import { autoTextColor } from '../../utils/colors.js';
import { DEWEY_DEFAULT_COLORS } from '../../utils/domain.js';

const { defineComponent, ref, computed, watch } = Vue;
const { useI18n } = VueI18n;

const DEFAULT_COLORS = DEWEY_DEFAULT_COLORS;

// Subdivisions codes per class (index 0-9, 10 entries each)
const SUBDIV_CODES = Array.from({ length: 10 }, (_, cls) =>
    Array.from({ length: 10 }, (_, i) => String(cls * 100 + i * 10).padStart(3, '0'))
);

export default defineComponent({
    name: 'DeweyPicker',

    props: {
        modelValue: {
            type: String,
            default: ''
        },
        colors: {
            type: Array,
            default: () => DEFAULT_COLORS
        },
        placeholder: {
            type: String,
            default: ''
        },
        inputClass: {
            type: String,
            default: ''
        },
        showBadge: {
            type: Boolean,
            default: true
        }
    },

    emits: ['update:modelValue'],

    setup(props, { emit }) {
        const { t } = useI18n();

        const open = ref(false);
        const selectedClass = ref(null);

        const resolvedColors = computed(() =>
            (props.colors && props.colors.length === 10) ? props.colors : DEFAULT_COLORS
        );

        // Badge: derived from first digit of current value
        const badgeClass = computed(() => {
            const first = (props.modelValue || '').trim()[0];
            if (first >= '0' && first <= '9') return parseInt(first);
            return null;
        });

        const badgeStyle = computed(() => {
            if (badgeClass.value === null) return { background: 'transparent', color: 'inherit' };
            const hex = resolvedColors.value[badgeClass.value];
            if (!hex) return { background: 'transparent', color: 'inherit' };
            const outline = (hex === '#ffffff' || hex === '#fff') ? '1px solid #ddd' : 'none';
            return { background: hex, color: autoTextColor(hex), outline };
        });

        const badgeText = computed(() =>
            badgeClass.value !== null ? String(badgeClass.value) : '?'
        );

        // Class buttons
        const classButtons = computed(() =>
            resolvedColors.value.map((hex, n) => ({
                n,
                hex: hex || '#cccccc',
                textColor: hex ? autoTextColor(hex) : '#ffffff',
                border: (!hex || hex === '#ffffff' || hex === '#fff') ? '2px solid #ccc' : '2px solid transparent',
                label: t(`dewey.class.${n}`),
                selected: selectedClass.value === n
            }))
        );

        // Subdivision buttons for selected class
        const subdivisionButtons = computed(() => {
            if (selectedClass.value === null) return [];
            const n = selectedClass.value;
            const hex = resolvedColors.value[n] || '#cccccc';
            return SUBDIV_CODES[n].map(code => ({
                code,
                label: t(`dewey.sub.${code}`),
                borderColor: hex
            }));
        });

        const subdivHeader = computed(() => {
            if (selectedClass.value === null) return '';
            const n = selectedClass.value;
            return `${n * 100}–${n * 100 + 99} · ${t(`dewey.class_full.${n}`)}`;
        });

        function selectClass(n) {
            selectedClass.value = n;
        }

        function insert(code) {
            const cur = (props.modelValue || '').trim();
            const spaceIdx = cur.indexOf(' ');

            let deweyPart, authorSuffix;
            if (spaceIdx >= 0) {
                // "551.46 VER" or "551 VER" — space separates dewey from author
                deweyPart = cur.slice(0, spaceIdx);
                authorSuffix = cur.slice(spaceIdx); // ' VER'
            } else if (cur.length > 0 && cur[0] >= 'A' && cur[0] <= 'Z') {
                // "VER" alone — pure author string, no dewey yet
                deweyPart = '';
                authorSuffix = ' ' + cur;
            } else {
                // "551.46" or "" — pure dewey part
                deweyPart = cur;
                authorSuffix = '';
            }

            // Keep decimal part of existing dewey (.46), add bare dot only if no author follows
            const dotIdx = deweyPart.indexOf('.');
            const decimalSuffix = dotIdx >= 0 ? deweyPart.slice(dotIdx) : (authorSuffix ? '' : '.');

            emit('update:modelValue', code + decimalSuffix + authorSuffix);
            open.value = false;
        }

        function onInput(e) {
            emit('update:modelValue', e.target.value);
        }

        function toggle() {
            open.value = !open.value;
        }

        // Close on outside click
        function onDocClick(e) {
            if (!e.target.closest('.dewey-picker-wrap')) {
                open.value = false;
            }
        }

        // Using onMounted/onUnmounted via lifecycle
        const { onMounted, onUnmounted } = Vue;
        onMounted(() => document.addEventListener('click', onDocClick));
        onUnmounted(() => document.removeEventListener('click', onDocClick));

        return {
            open, selectedClass,
            badgeStyle, badgeText,
            classButtons, subdivisionButtons, subdivHeader,
            selectClass, insert, onInput, toggle,
            t
        };
    },

    template: `
<div class="dewey-picker-wrap">
  <!-- Input row -->
  <div class="d-flex gap-2 align-items-stretch">
    <div class="dewey-input-group d-flex flex-grow-1" style="border:1.5px solid #ccc; border-radius:6px; overflow:hidden; transition:border-color .15s;">
      <!-- Badge coloré -->
      <div
        v-if="showBadge"
        class="dewey-badge d-flex align-items-center justify-content-center flex-shrink-0"
        :style="[badgeStyle, {minWidth:'2rem', fontSize:'.7rem', fontWeight:'700', userSelect:'none', padding:'0 .3rem'}]"
      >{{ badgeText }}</div>
      <!-- Champ libre -->
      <input
        type="text"
        :value="modelValue"
        :placeholder="placeholder || t('dewey.input_placeholder')"
        :class="['form-control border-0 rounded-0', inputClass]"
        style="font-family:monospace; box-shadow:none;"
        @input="onInput"
      />
    </div>
    <!-- Bouton toggle -->
    <button
      type="button"
      :class="['btn btn-sm border', open ? 'btn-primary' : 'btn-outline-secondary']"
      style="white-space:nowrap; flex-shrink:0;"
      @click.stop="toggle"
    >{{ open ? t('dewey.btn_close') : t('dewey.btn_open') }}</button>
  </div>

  <!-- Picker panel -->
  <div v-if="open" class="dewey-picker-panel border rounded mt-1 p-2 bg-white shadow-sm">

    <!-- Niveau 1 : classes -->
    <div class="d-flex gap-1 mb-0">
      <button
        v-for="cls in classButtons"
        :key="cls.n"
        type="button"
        class="dewey-cls-btn flex-fill border rounded py-1 px-0"
        :style="{
          background: cls.hex,
          color: cls.textColor,
          border: cls.border + ' !important',
          fontSize: '.65rem',
          fontWeight: '700',
          lineHeight: '1.2',
          outline: cls.selected ? '2px solid #1a1a1a' : 'none',
          outlineOffset: '-2px'
        }"
        @click.stop="selectClass(cls.n)"
      >
        <span style="display:block; font-size:.75rem;">{{ cls.n }}</span>
        <span style="display:block; font-size:.55rem; font-weight:400;">{{ cls.label }}</span>
      </button>
    </div>

    <!-- Niveau 2 : subdivisions -->
    <div v-if="selectedClass !== null" class="mt-2 pt-2 border-top">
      <div class="text-muted mb-1" style="font-size:.72rem; font-weight:500;">{{ subdivHeader }}</div>
      <div class="row g-1">
        <div v-for="sub in subdivisionButtons" :key="sub.code" class="col-6">
          <button
            type="button"
            class="btn btn-sm w-100 text-start border py-1 px-2"
            style="font-size:.75rem; background:#f9f9f9; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"
            :style="{'border-left': '3px solid ' + sub.borderColor + ' !important'}"
            :title="sub.code + ' · ' + sub.label"
            @click.stop="insert(sub.code)"
          ><strong style="font-family:monospace;">{{ sub.code }}</strong> {{ sub.label }}</button>
        </div>
      </div>
    </div>
  </div>
</div>
    `
});
