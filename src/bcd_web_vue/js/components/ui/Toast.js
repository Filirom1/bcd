/**
 * Toast Component
 * Individual notification toast with auto-dismiss
 */

const { defineComponent, onMounted } = Vue;
import { useNotification } from '../../composables/useNotification.js';

export default defineComponent({
    name: 'Toast',

    props: {
        notification: {
            type: Object,
            required: true
        }
    },

    setup(props) {
        const { dismiss } = useNotification();

        onMounted(() => {
            if (props.notification.duration) {
                setTimeout(() => {
                    dismiss(props.notification.id);
                }, props.notification.duration);
            }
        });

        const getTypeClass = () => {
            const typeMap = {
                success: 'bg-success',
                error: 'bg-danger',
                warning: 'bg-warning',
                info: 'bg-info'
            };
            return typeMap[props.notification.type] || 'bg-secondary';
        };

        const getIcon = () => {
            const iconMap = {
                success: 'bi-check-circle-fill',
                error: 'bi-exclamation-circle-fill',
                warning: 'bi-exclamation-triangle-fill',
                info: 'bi-info-circle-fill'
            };
            return iconMap[props.notification.type] || 'bi-bell-fill';
        };

        return {
            dismiss,
            getTypeClass,
            getIcon
        };
    },

    template: `
        <div
            class="toast show"
            :class="getTypeClass()"
            role="alert"
            aria-live="assertive"
            aria-atomic="true"
        >
            <div class="toast-body text-white d-flex align-items-start">
                <div class="flex-grow-1">
                    {{ notification.message || notification.title }}
                </div>
                <button
                    type="button"
                    class="btn-close btn-close-white ms-2"
                    @click="dismiss(notification.id)"
                    aria-label="Close"
                ></button>
            </div>
        </div>
    `
});
