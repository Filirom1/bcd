/**
 * Shared card shell for page panels. Keeps the app's Bootstrap-compatible
 * card structure and lets pages supply their own header, body, and footer.
 */

const { defineComponent } = Vue;

export default defineComponent({
    name: 'PanelCard',

    props: {
        body: { type: Boolean, default: true },
        bodyClass: { type: String, default: '' }
    },

    template: `
        <section class="card">
            <div v-if="$slots.header" class="card-header">
                <slot name="header" />
            </div>
            <div v-if="body" :class="['card-body', bodyClass]">
                <slot />
            </div>
            <slot v-else />
            <div v-if="$slots.footer" class="card-footer">
                <slot name="footer" />
            </div>
        </section>
    `
});
