/**
 * Loading Spinner Component
 * Bootstrap spinner with optional text
 */

const { defineComponent } = Vue;

export default defineComponent({
    name: 'LoadingSpinner',

    props: {
        text: {
            type: String,
            default: 'Chargement...'
        },
        size: {
            type: String,
            default: 'md',
            validator: (value) => ['sm', 'md', 'lg'].includes(value)
        },
        variant: {
            type: String,
            default: 'primary'
        }
    },

    computed: {
        spinnerClass() {
            return `spinner-border text-${this.variant}`;
        },

        sizeClass() {
            return this.size === 'sm' ? 'spinner-border-sm' : '';
        }
    },

    template: `
        <div class="text-center p-4">
            <div
                :class="[spinnerClass, sizeClass]"
                role="status"
            >
                <span class="visually-hidden">{{ text }}</span>
            </div>
            <p v-if="text" class="mt-2 text-muted">{{ text }}</p>
        </div>
    `
});
