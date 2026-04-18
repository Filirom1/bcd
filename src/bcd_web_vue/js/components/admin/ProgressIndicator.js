/**
 * ProgressIndicator - Reusable progress indicator for bulk operations
 *
 * Displays a progress bar with percentage for operations affecting ≥100 records.
 * For smaller operations, shows a simple spinner.
 *
 * Constitution Principle VI: Performance for Legacy Hardware
 * - Progress feedback required for operations taking >2 seconds
 */

const { defineComponent, computed } = Vue;

export default defineComponent({
    name: 'ProgressIndicator',
    props: {
        /**
         * Current progress (0-100)
         */
        progress: {
            type: Number,
            default: 0,
            validator: (value) => value >= 0 && value <= 100
        },
        /**
         * Total number of items being processed
         */
        total: {
            type: Number,
            default: 0
        },
        /**
         * Number of items processed so far
         */
        processed: {
            type: Number,
            default: 0
        },
        /**
         * Operation description
         */
        operation: {
            type: String,
            default: ''
        },
        /**
         * Show as percentage bar (for ≥100 items)
         * If false, shows spinner (for <100 items)
         */
        showPercentage: {
            type: Boolean,
            default: false
        },
        /**
         * Variant (primary, success, warning, danger)
         */
        variant: {
            type: String,
            default: 'primary',
            validator: (value) => ['primary', 'success', 'warning', 'danger'].includes(value)
        }
    },
    setup(props) {
        const progressBarClass = computed(() => {
            return `progress-bar bg-${props.variant}`;
        });

        const progressText = computed(() => {
            if (props.total > 0) {
                return `${props.processed} / ${props.total}`;
            }
            return `${props.progress}%`;
        });

        const estimatedTime = computed(() => {
            if (props.processed === 0 || props.total === 0) {
                return null;
            }

            // Estimate based on average time per item
            const remaining = props.total - props.processed;
            if (remaining <= 0) {
                return null;
            }

            // Simple estimation (can be improved with actual timing data)
            const secondsRemaining = Math.ceil(remaining * 0.05); // ~50ms per item
            if (secondsRemaining < 60) {
                return `~${secondsRemaining}s remaining`;
            }
            const minutesRemaining = Math.ceil(secondsRemaining / 60);
            return `~${minutesRemaining}m remaining`;
        });

        return {
            progressBarClass,
            progressText,
            estimatedTime
        };
    },
    template: `
        <div class="progress-indicator">
            <!-- Spinner for small operations (<100 items) -->
            <div v-if="!showPercentage" class="text-center py-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 mb-0 text-muted" v-if="operation">{{ operation }}</p>
            </div>

            <!-- Progress bar for large operations (≥100 items) -->
            <div v-else class="progress-container">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="fw-medium">{{ operation }}</span>
                    <span class="text-muted small">{{ progressText }}</span>
                </div>
                <div class="progress" style="height: 24px;">
                    <div
                        :class="progressBarClass"
                        role="progressbar"
                        :style="{ width: progress + '%' }"
                        :aria-valuenow="progress"
                        aria-valuemin="0"
                        aria-valuemax="100"
                    >
                        {{ progress }}%
                    </div>
                </div>
                <div v-if="estimatedTime" class="text-muted small mt-1 text-end">
                    {{ estimatedTime }}
                </div>
            </div>
        </div>
    `
});
