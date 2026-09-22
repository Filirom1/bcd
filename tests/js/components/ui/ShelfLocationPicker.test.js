import { afterEach, describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import ShelfLocationPicker from '../../../../src/bcd_web_vue/js/components/ui/ShelfLocationPicker.js';

afterEach(() => {
    document.body.innerHTML = '';
});

function mountPicker(props = {}) {
    return mount(ShelfLocationPicker, {
        props: {
            locations: [
                { label: 'Romans', color: '#000000' },
                { label: 'Documentaires', color: null }
            ],
            ...props
        }
    });
}

describe('ShelfLocationPicker', () => {
    it('emits typed values and displays the configured color badge', async () => {
        const wrapper = mountPicker({ modelValue: 'Romans' });
        const input = wrapper.get('input[type="text"]');

        expect(wrapper.vm.hasBadgeColor).toBe('#000000');
        expect(wrapper.vm.badgeStyle.background).toBe('#000000');
        await input.setValue('New shelf');
        expect(wrapper.emitted('update:modelValue')).toEqual([['New shelf']]);
    });

    it('opens the location selector and emits a selected location or clear option', async () => {
        const wrapper = mountPicker({ extraOptions: [{ label: '__clear__', display: 'Clear' }] });
        await wrapper.get('button').trigger('click');
        expect(wrapper.vm.open).toBe(true);
        expect(wrapper.find('.panel').exists()).toBe(false); // panel has no special class
        expect(wrapper.findAll('.shelf-picker-wrap .btn-sm')).toHaveLength(4);

        const panelButtons = wrapper.findAll('.shelf-picker-wrap .border.rounded.mt-1 button');
        await panelButtons[0].trigger('click');
        expect(wrapper.emitted('update:modelValue')[0]).toEqual(['Romans']);
        expect(wrapper.vm.open).toBe(false);

        await wrapper.get('button').trigger('click');
        const buttons = wrapper.findAll('.shelf-picker-wrap .border.rounded.mt-1 button');
        await buttons[buttons.length - 1].trigger('click');
        expect(wrapper.emitted('update:modelValue')).toContainEqual(['__clear__']);
    });

    it('handles an unknown and empty location without a colored badge', () => {
        const unknown = mountPicker({ modelValue: 'Unknown' });
        expect(unknown.vm.hasBadgeColor).toBeFalsy();
        expect(unknown.vm.badgeStyle.background).toBe('transparent');

        const empty = mountPicker({ modelValue: '' });
        expect(empty.vm.hasBadgeColor).toBeFalsy();
    });

    it('closes its panel when the document is clicked outside', async () => {
        const wrapper = mountPicker();
        await wrapper.get('button').trigger('click');
        expect(wrapper.vm.open).toBe(true);

        document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        expect(wrapper.vm.open).toBe(false);
    });
});
