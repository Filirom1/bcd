/**
 * App-wide, blocking alert shown when a returned item makes a hold ready.
 * The librarian must acknowledge the instruction before continuing to scan.
 */
const { defineComponent, ref, watch, nextTick } = Vue;
const { useI18n } = VueI18n;
import Modal from '../ui/Modal.js';
import { useHoldReadyModal } from '../../composables/useHoldReadyModal.js';
import { formatCivilDate } from '../../utils/date.js';

export default defineComponent({
    name: 'HoldReadyModal',

    components: { Modal },

    setup() {
        const { t, locale } = useI18n();
        const { holdReady, dismissHoldReady } = useHoldReadyModal();
        const acknowledgeButton = ref(null);

        watch(holdReady, async (data) => {
            if (!data) return;
            await nextTick();
            acknowledgeButton.value?.focus();
        }, { immediate: true });

        const formattedExpirationDate = () => {
            if (!holdReady.value?.expiration_date) return '';
            return formatCivilDate(holdReady.value.expiration_date, locale.value);
        };

        return {
            t,
            holdReady,
            dismissHoldReady,
            acknowledgeButton,
            formattedExpirationDate
        };
    },

    template: `
        <modal
            :show="holdReady !== null"
            :title="t('circulation.hold_ready_title')"
            size="lg"
            :static="true"
            :show-close="false"
            centered
            @close="dismissHoldReady"
        >
            <div v-if="holdReady" class="text-center py-2" role="alert" aria-live="assertive">
                <i class="bi bi-bookmark-star-fill display-2 text-warning" aria-hidden="true"></i>
                <p class="fs-3 fw-bold mt-3 mb-4">
                    {{ t('circulation.hold_ready_instruction') }}
                </p>

                <div class="rounded-3 border border-warning bg-warning-subtle p-4 mx-auto">
                    <div class="text-uppercase small fw-bold text-muted mb-1">
                        {{ t('circulation.hold_ready_book_label') }}
                    </div>
                    <h2 class="h3 fw-bold mb-3">{{ holdReady.title || holdReady.item_id }}</h2>

                    <div class="fs-5">
                        {{ t('circulation.hold_ready_message', {
                            name: holdReady.borrower_name || holdReady.borrower_id,
                            class: holdReady.class_name || holdReady.borrower_id
                        }) }}
                    </div>

                    <div v-if="holdReady.item_id" class="mt-2">
                        <span class="text-muted">{{ t('catalog.inventory_number') }} :</span>
                        <code class="fs-5 ms-1">{{ holdReady.item_id }}</code>
                    </div>

                    <div v-if="holdReady.expiration_date" class="mt-2 text-muted">
                        {{ t('circulation.hold_expires') }} {{ formattedExpirationDate() }}
                    </div>
                </div>
            </div>

            <template #footer>
                <button
                    ref="acknowledgeButton"
                    type="button"
                    class="btn btn-primary btn-lg w-100"
                    @click="dismissHoldReady"
                >
                    <i class="bi bi-check-lg me-2" aria-hidden="true"></i>
                    {{ t('circulation.hold_ready_acknowledge') }}
                </button>
            </template>
        </modal>
    `
});
