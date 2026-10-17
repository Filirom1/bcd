const { defineComponent, computed, ref, watch } = Vue;
const { useI18n } = VueI18n;
import { useBookActionFeedback } from '../../composables/useBookActionFeedback.js';

export default defineComponent({
    name: 'BookActionFeedback',

    setup() {
        const { t } = useI18n();
        const { activeBookActionFeedback } = useBookActionFeedback();
        const coverLoadFailed = ref(false);
        watch(() => activeBookActionFeedback.value?.id, () => {
            coverLoadFailed.value = false;
        });
        const coverUrl = computed(() => {
            const cover = activeBookActionFeedback.value?.item.cover_image;
            return cover && !coverLoadFailed.value ? `/covers/${encodeURIComponent(cover)}` : '';
        });
        const confettiPieces = Array.from({ length: 14 }, (_, index) => index);

        return { activeBookActionFeedback, coverUrl, coverLoadFailed, confettiPieces, t };
    },

    template: `
        <transition name="book-action-feedback">
            <div
                :key="activeBookActionFeedback?.id"
                v-if="activeBookActionFeedback"
                class="book-action-feedback-overlay"
                :class="'is-' + activeBookActionFeedback.action"
                role="status"
                aria-live="polite"
                :aria-label="t(activeBookActionFeedback.action === 'checkout' ? 'circulation.book_action_checkout' : 'circulation.book_action_return')"
            >
                <div class="book-action-feedback-confetti" aria-hidden="true">
                    <span v-for="piece in confettiPieces" :key="piece" :class="'piece-' + piece"></span>
                </div>
                <div class="book-action-feedback-content">
                    <div class="book-action-feedback-sparkle" aria-hidden="true">✦</div>
                    <div class="book-action-feedback-kicker">
                        <i class="bi bi-stars me-2" aria-hidden="true"></i>
                        {{ t(activeBookActionFeedback.action === 'checkout' ? 'circulation.book_action_checkout' : 'circulation.book_action_return') }}
                    </div>
                    <div class="book-action-feedback-card">
                        <div class="book-action-feedback-bonus" aria-hidden="true">
                            <i
                                class="bi"
                                :class="activeBookActionFeedback.action === 'checkout' ? 'bi-book-half' : 'bi-arrow-return-left'"
                            ></i>
                            <span>{{ activeBookActionFeedback.action === 'checkout' ? '+1' : 'OK' }}</span>
                        </div>
                        <div class="book-action-feedback-book">
                            <img
                                v-if="coverUrl"
                                :src="coverUrl"
                                :alt="activeBookActionFeedback.item.title"
                                class="book-action-feedback-cover"
                                @error="coverLoadFailed = true"
                            />
                            <div v-else class="book-action-feedback-placeholder">
                                <i class="bi bi-book-half" aria-hidden="true"></i>
                                <span>{{ activeBookActionFeedback.item.title }}</span>
                            </div>
                        </div>
                        <div class="book-action-feedback-details">
                            <div class="book-action-feedback-label">{{ t('circulation.book_action_book_label') }}</div>
                            <h2>{{ activeBookActionFeedback.item.title }}</h2>
                            <p>
                                <i class="bi bi-pen me-2" aria-hidden="true"></i>
                                {{ activeBookActionFeedback.item.authors.length ? activeBookActionFeedback.item.authors.join(', ') : t('catalog.unknown_author') }}
                            </p>
                            <p v-if="activeBookActionFeedback.item.illustrators.length">
                                <i class="bi bi-palette me-2" aria-hidden="true"></i>
                                {{ activeBookActionFeedback.item.illustrators.join(', ') }}
                            </p>
                            <small v-if="activeBookActionFeedback.item.item_id">
                                {{ t('catalog.inventory_number') }} · {{ activeBookActionFeedback.item.item_id }}
                            </small>
                        </div>
                    </div>
                    <div class="book-action-feedback-sparkle" aria-hidden="true">✦</div>
                    <div class="book-action-feedback-trail" aria-hidden="true"></div>
                </div>
            </div>
        </transition>
    `
});
