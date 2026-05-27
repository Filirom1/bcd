/**
 * ShelfLocationPicker Component
 *
 * Shelf location input with color badge preview.
 * - Colored badge on the left of the input, derived from the matched location
 * - Toggle button opens a panel with clickable location buttons (colored)
 * - Free-text entry still supported
 * - Colors come from the `locations` prop (array of {label, color})
 *
 * Usage:
 *   <shelf-location-picker v-model="shelfLocation" :locations="shelfLocationOptions" />
 */

import { autoTextColor } from '../../utils/colors.js';

const { defineComponent, ref, computed } = Vue;
const { useI18n } = VueI18n;

export default defineComponent({
    name: 'ShelfLocationPicker',

    props: {
        modelValue: {
            type: String,
            default: ''
        },
        locations: {
            type: Array,
            default: () => []
        },
        placeholder: {
            type: String,
            default: ''
        },
        inputClass: {
            type: String,
            default: ''
        },
        // Extra options prepended to the panel (e.g. {label: '__clear__', color: null})
        extraOptions: {
            type: Array,
            default: () => []
        }
    },

    emits: ['update:modelValue'],

    setup(props, { emit }) {
        const { t } = useI18n();
        const open = ref(false);

        // Match current value against locations list
        const matchedEntry = computed(() => {
            const val = (props.modelValue || '').trim();
            if (!val) return null;
            return props.locations.find(e => e.label === val) || null;
        });

        const badgeStyle = computed(() => {
            const base = { minWidth: '0.5rem', width: '0.5rem', flexShrink: 0 };
            const entry = matchedEntry.value;
            if (!entry || !entry.color) return { ...base, background: 'transparent' };
            return { ...base, background: entry.color };
        });

        const hasBadgeColor = computed(() => {
            return matchedEntry.value && matchedEntry.value.color;
        });

        // Buttons for each location in the panel
        const locationButtons = computed(() =>
            props.locations.map(entry => {
                const hex = entry.color || null;
                return {
                    label: entry.label,
                    hex,
                    textColor: hex ? autoTextColor(hex) : 'inherit',
                    style: hex
                        ? { background: hex, color: autoTextColor(hex), border: '2px solid transparent' }
                        : { background: '#f8f9fa', color: 'inherit', border: '2px solid #dee2e6' }
                };
            })
        );

        function select(label) {
            emit('update:modelValue', label);
            open.value = false;
        }

        function onInput(e) {
            emit('update:modelValue', e.target.value);
        }

        function toggle() {
            open.value = !open.value;
        }

        const { onMounted, onUnmounted } = Vue;

        function onDocClick(e) {
            if (!e.target.closest('.shelf-picker-wrap')) {
                open.value = false;
            }
        }

        onMounted(() => document.addEventListener('click', onDocClick));
        onUnmounted(() => document.removeEventListener('click', onDocClick));

        return {
            open, badgeStyle, hasBadgeColor, locationButtons,
            select, onInput, toggle, t
        };
    },

    template: `
<div class="shelf-picker-wrap">
  <!-- Input row -->
  <div class="d-flex gap-2 align-items-stretch">
    <div class="d-flex flex-grow-1 align-items-stretch" style="border:1.5px solid #ccc; border-radius:6px; overflow:hidden; transition:border-color .15s;">
      <!-- Colored strip -->
      <div
        class="flex-shrink-0"
        :style="[badgeStyle, { transition: 'background .2s' }]"
      ></div>
      <!-- Text input -->
      <input
        type="text"
        :value="modelValue"
        :placeholder="placeholder || t('catalog.shelf_location_placeholder')"
        :class="['form-control border-0 rounded-0', inputClass]"
        style="box-shadow:none;"
        @input="onInput"
      />
    </div>
    <!-- Toggle button -->
    <button
      v-if="locations.length"
      type="button"
      :class="['btn btn-sm border', open ? 'btn-primary' : 'btn-outline-secondary']"
      style="white-space:nowrap; flex-shrink:0;"
      @click.stop="toggle"
    >{{ open ? t('catalog.shelf_picker_close') : t('catalog.shelf_picker_open') }}</button>
  </div>

  <!-- Panel -->
  <div v-if="open && locations.length" class="border rounded mt-1 p-2 bg-white shadow-sm">
    <div class="d-flex flex-wrap gap-1">
      <button
        v-for="btn in locationButtons"
        :key="btn.label"
        type="button"
        class="btn btn-sm"
        :style="btn.style"
        @click.stop="select(btn.label)"
      >{{ btn.label }}</button>
      <button
        v-for="opt in extraOptions"
        :key="opt.label"
        type="button"
        class="btn btn-sm btn-outline-secondary"
        @click.stop="select(opt.label)"
      >{{ opt.display || opt.label }}</button>
    </div>
  </div>
</div>
    `
});
