import { afterEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import HoldReadyModal from '../../../../src/bcd_web_vue/js/components/circulation/HoldReadyModal.js';
import { useHoldReadyModal } from '../../../../src/bcd_web_vue/js/composables/useHoldReadyModal.js';
import { setTestTranslator } from '../../helpers/i18n.js';

const clearQueue = () => {
    const modal = useHoldReadyModal();
    while (modal.holdReady.value) modal.dismissHoldReady();
};

afterEach(clearQueue);

describe('HoldReadyModal', () => {
    it('shows a blocking alert with the item and reservation details and focuses acknowledgement', async () => {
        setTestTranslator((key, params) => key === 'circulation.hold_ready_message'
            ? `Set aside for ${params.name} (${params.class})`
            : key);
        useHoldReadyModal().showHoldReady(
            { borrower_name: 'Lina Martin', borrower_id: 'B-9', class_name: 'CE2', expiration_date: '2030-02-01' },
            { item_id: 'I-12', title: 'Le Petit Nicolas' }
        );
        const wrapper = mount(HoldReadyModal);
        await new Promise(resolve => setTimeout(resolve, 0));

        const dialog = document.body.querySelector('[role="dialog"]');
        const acknowledge = document.body.querySelector('.modal-footer button');

        expect(dialog?.getAttribute('aria-modal')).toBe('true');
        expect(document.body.textContent).toContain('Le Petit Nicolas');
        expect(document.body.textContent).toContain('Lina Martin');
        expect(document.body.textContent).toContain('I-12');
        expect(document.body.querySelector('.btn-close')).toBeNull();
        expect(document.activeElement).toBe(acknowledge);

        acknowledge.click();
        await wrapper.vm.$nextTick();
        expect(useHoldReadyModal().holdReady.value).toBeNull();
        wrapper.unmount();
    });
});
