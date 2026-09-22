import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import ScannedItemsList from '../../../../src/bcd_web_vue/js/components/circulation/ScannedItemsList.js';

describe('ScannedItemsList', () => {
    it('renders checkout items, dates, covers and errors', async () => {
        const wrapper = mount(ScannedItemsList, {
            props: {
                mode: 'checkout',
                items: [
                    { item_id: 'I-1', barcode: '.I-1', title: 'Book', author: 'Author', due_date: '2030-01-15', cover_image: 'cover.jpg' },
                    { item_id: 'I-2', error: true, error_message: 'Already loaned' }
                ]
            }
        });

        expect(wrapper.findAll('.list-group-item')).toHaveLength(2);
        expect(wrapper.find('img').attributes('src')).toBe('/covers/cover.jpg');
        expect(wrapper.text()).toContain('Book');
        expect(wrapper.vm.getItemClass({ error: true })).toBe('list-group-item-danger');
        expect(wrapper.vm.getItemClass({})).toBe('list-group-item-success');
        expect(wrapper.vm.getItemIcon({ error: true })).toContain('text-danger');
        expect(wrapper.vm.getItemIcon({})).toContain('text-success');

        await wrapper.findAll('.list-group-item').at(0).trigger('click');
        wrapper.vm.removeItem('I-1');
        expect(wrapper.emitted('remove-item')).toEqual([['I-1']]);
    });

    it('renders return-specific details including a ready hold', () => {
        const wrapper = mount(ScannedItemsList, {
            props: {
                mode: 'return',
                items: [{
                    item_id: 'I-2',
                    returned_date: '2030-01-16',
                    hold_ready: {
                        borrower_name: 'Amira',
                        borrower_id: 'B-1',
                        class_name: 'CM2',
                        expiration_date: '2030-01-20'
                    }
                }]
            }
        });

        expect(wrapper.vm.getItemClass({})).toBe('list-group-item-info');
        expect(wrapper.vm.getItemIcon({})).toBe('bi-arrow-return-left text-info');
        expect(wrapper.text()).toContain('circulation.hold_ready_message');
        expect(wrapper.text()).toContain('circulation.hold_expires');
    });

    it('renders nothing for an empty list', () => {
        const wrapper = mount(ScannedItemsList, { props: { mode: 'checkout', items: [] } });
        expect(wrapper.find('.card').exists()).toBe(false);
        expect(wrapper.vm.getItemClass({})).toBe('list-group-item-success');
    });
});
