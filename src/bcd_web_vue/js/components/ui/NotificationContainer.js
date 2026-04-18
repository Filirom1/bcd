/**
 * Notification Container Component
 * Renders all active toast notifications
 */

const { defineComponent } = Vue;
import { useNotification } from '../../composables/useNotification.js';
import Toast from './Toast.js';

export default defineComponent({
    name: 'NotificationContainer',

    components: {
        Toast
    },

    setup() {
        const { notifications } = useNotification();

        return {
            notifications
        };
    },

    template: `
        <div
            class="toast-container position-fixed top-0 end-0 p-3"
            style="z-index: 9999"
        >
            <transition-group name="toast">
                <toast
                    v-for="notification in notifications"
                    :key="notification.id"
                    :notification="notification"
                />
            </transition-group>
        </div>
    `
});
