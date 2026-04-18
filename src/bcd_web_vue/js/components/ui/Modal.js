/**
 * Modal Component — Pattern B (pure Vue, no Bootstrap JS)
 *
 * Props:
 *   show     (Boolean) — controls visibility
 *   title    (String)  — header title, overridden by slot#header
 *   size     (String)  — sm | md | lg | xl  (default: md)
 *   static   (Boolean) — if true, backdrop click and ESC don't close (default: false)
 *   centered (Boolean) — vertically centered dialog (default: false)
 *   scrollable (Boolean) — scrollable body (default: false)
 *
 * Emits: close
 * Slots: header, default (body), footer
 */

const { defineComponent, onMounted, onUnmounted } = Vue;

export default defineComponent({
    name: 'Modal',

    props: {
        show: {
            type: Boolean,
            default: false
        },
        title: {
            type: String,
            default: ''
        },
        size: {
            type: String,
            default: 'md',
            validator: (v) => ['sm', 'md', 'lg', 'xl'].includes(v)
        },
        static: {
            type: Boolean,
            default: false
        },
        centered: {
            type: Boolean,
            default: false
        },
        scrollable: {
            type: Boolean,
            default: false
        }
    },

    emits: ['close'],

    setup(props, { emit }) {
        const close = () => emit('close');
        const onBackdropClick = () => { if (!props.static) close(); };
        const onKeydown = (e) => { if (e.key === 'Escape' && !props.static) close(); };

        onMounted(() => document.addEventListener('keydown', onKeydown));
        onUnmounted(() => document.removeEventListener('keydown', onKeydown));

        return { close, onBackdropClick };
    },

    template: `
        <teleport to="body">
            <div v-if="show">
                <div
                    class="modal fade show d-block"
                    tabindex="-1"
                    role="dialog"
                    @click.self="onBackdropClick"
                >
                    <div
                        :class="[
                            'modal-dialog',
                            'modal-' + size,
                            centered && 'modal-dialog-centered',
                            scrollable && 'modal-dialog-scrollable'
                        ]"
                    >
                        <div class="modal-content">
                            <!-- Header -->
                            <div class="modal-header">
                                <h5 class="modal-title">
                                    <slot name="header">{{ title }}</slot>
                                </h5>
                                <button
                                    type="button"
                                    class="btn-close"
                                    @click="close"
                                    aria-label="Close"
                                ></button>
                            </div>

                            <!-- Body -->
                            <div class="modal-body">
                                <slot></slot>
                            </div>

                            <!-- Footer -->
                            <div v-if="$slots.footer" class="modal-footer">
                                <slot name="footer"></slot>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-backdrop fade show"></div>
            </div>
        </teleport>
    `
});
