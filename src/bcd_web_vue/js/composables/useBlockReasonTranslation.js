const { useI18n } = VueI18n;

/**
 * Composable for translating block reasons
 * Maps database values (in English) to i18n keys for proper translation
 */
export function useBlockReasonTranslation() {
    const { t } = useI18n();

    // Map database values (English) to i18n keys
    const reasonKeyMap = {
        'Lost Book': 'borrowers.reason_lost_book',
        'Damaged Materials': 'borrowers.reason_damaged',
        'Repeated Overdue Items': 'borrowers.reason_overdue',
        'Policy Violation': 'borrowers.reason_policy',
        'Other': 'borrowers.reason_other'
    };

    /**
     * Translate a block reason from database value to localized string
     * @param {string} reason - The block reason stored in the database
     * @returns {string} - The translated block reason
     */
    const translateBlockReason = (reason) => {
        if (!reason) return '';

        // If we have a mapping, use it
        const i18nKey = reasonKeyMap[reason];
        if (i18nKey) {
            return t(i18nKey);
        }

        // Fallback: return the raw value if no mapping found
        return reason;
    };

    return {
        translateBlockReason
    };
}
