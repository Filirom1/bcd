/**
 * FilterSelect Component
 * Dropdown filter with v-model support
 */

const { defineComponent } = Vue;

export default defineComponent({
    name: 'FilterSelect',

    props: {
        modelValue: {
            type: [String, Number],
            default: ''
        },
        options: {
            type: Array,
            required: true
        },
        label: {
            type: String,
            default: ''
        },
        placeholder: {
            type: String,
            default: 'Select...'
        },
        showPlaceholder: {
            type: Boolean,
            default: true
        }
    },

    emits: ['update:modelValue'],

    setup(props, { emit }) {
        const onChange = (event) => {
            emit('update:modelValue', event.target.value);
        };

        return {
            onChange
        };
    },

    template: `
        <div class="filter-select">
            <label v-if="label" class="form-label">{{ label }}</label>
            <select
                class="form-select"
                :value="modelValue"
                @change="onChange"
            >
                <option v-if="showPlaceholder" value="">{{ placeholder }}</option>
                <option
                    v-for="option in options"
                    :key="option.value"
                    :value="option.value"
                >
                    {{ option.label }}
                </option>
            </select>
        </div>
    `
});
