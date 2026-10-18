/**
 * Shared page-level heading layout.
 * Pages provide their own translated title and optional actions.
 */

const { defineComponent } = Vue;

export default defineComponent({
    name: 'PageHeader',

    template: `
        <header class="page-header">
            <div class="page-header-content">
                <slot name="heading" />
            </div>
            <div v-if="$slots.actions" class="page-header-actions">
                <slot name="actions" />
            </div>
        </header>
    `
});
