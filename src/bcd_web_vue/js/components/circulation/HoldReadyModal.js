/**
 * App-wide, blocking alert shown when a returned item makes a hold ready.
 * The librarian must acknowledge the instruction before continuing to scan.
 */
const { defineComponent, ref, computed, watch, nextTick } = Vue;
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
        const coverLoadFailed = ref(false);
        const coverUrl = computed(() => {
            const cover = holdReady.value?.cover_image?.trim();
            return cover ? `/covers/${encodeURIComponent(cover)}` : '';
        });

        watch(holdReady, async (data) => {
            coverLoadFailed.value = false;
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
            formattedExpirationDate,
            coverUrl,
            coverLoadFailed
        };
    },

    template: `
        <modal
                :show="holdReady !== null"
                :title="t('circulation.hold_ready_title')"
                content-class="hold-ready-modal"
                size="lg"
                :static="true"
                :show-close="false"
                :priority="true"
                centered
                @close="dismissHoldReady"
        >
                <div v-if="holdReady" class="hold-ready-content text-center" role="alert" aria-live="assertive">
                    <i class="bi bi-bookmark-star-fill hold-ready-icon" aria-hidden="true"></i>
                    <p class="hold-ready-instruction">
                        {{ t('circulation.hold_ready_instruction') }}
                    </p>

                    <div class="hold-ready-book-card" :class="{ 'has-cover': coverUrl && !coverLoadFailed }">
                        <img
                            v-if="coverUrl && !coverLoadFailed"
                            :src="coverUrl"
                            :alt="holdReady.title || ''"
                            class="hold-ready-cover"
                            @error="coverLoadFailed = true"
                        />
                        <div class="hold-ready-book-details">
                            <div class="hold-ready-book-label">{{ t('circulation.hold_ready_book_label') }}</div>
                            <h2>{{ holdReady.title || holdReady.item_id }}</h2>
                            <div class="hold-ready-borrower">
                                {{ t('circulation.hold_ready_message', {
                                    name: holdReady.borrower_name || holdReady.borrower_id,
                                    class: holdReady.class_name || holdReady.borrower_id
                                }) }}
                            </div>
                            <div v-if="holdReady.item_id" class="hold-ready-meta">
                                <span>{{ t('catalog.inventory_number') }} :</span>
                                <code>{{ holdReady.item_id }}</code>
                            </div>
                            <div v-if="holdReady.expiration_date" class="hold-ready-meta hold-ready-expiration">
                                {{ t('circulation.hold_expires') }} {{ formattedExpirationDate() }}
                            </div>
                        </div>
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
