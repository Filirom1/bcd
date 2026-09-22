import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import DeweyPicker from '../../../../src/bcd_web_vue/js/components/ui/DeweyPicker.js';

describe('DeweyPicker', () => {
    it('renders badge and picker button when enabled', async () => {
        const wrapper = mount(DeweyPicker, {
            props: {
                modelValue: '840 DUM',
                enabled: true
            },
            global: {
                mocks: {
                    $t: (key) => key,
                    t: (key) => key
                }
            }
        });

        expect(wrapper.find('.dewey-badge').text()).toBe('8');
        expect(wrapper.find('button').exists()).toBe(true);

        // Open picker
        await wrapper.find('button').trigger('click');
        expect(wrapper.vm.open).toBe(true);
        expect(wrapper.find('.dewey-picker-panel').exists()).toBe(true);
    });

    it('hides picker button and disables colored badge when dewey is disabled', () => {
        const wrapper = mount(DeweyPicker, {
            props: {
                modelValue: '840 DUM',
                enabled: false
            },
            global: {
                mocks: {
                    $t: (key) => key,
                    t: (key) => key
                }
            }
        });

        expect(wrapper.find('.dewey-badge').text()).toBe('?');
        expect(wrapper.find('button').exists()).toBe(false);
    });

    it('emits update:modelValue on text input', async () => {
        const wrapper = mount(DeweyPicker, {
            props: {
                modelValue: '',
                enabled: false
            },
            global: {
                mocks: {
                    $t: (key) => key,
                    t: (key) => key
                }
            }
        });

        const input = wrapper.find('input');
        await input.setValue('123.4');

        expect(wrapper.emitted('update:modelValue')).toBeTruthy();
        expect(wrapper.emitted('update:modelValue')[0]).toEqual(['123.4']);
    });

    it('selects a Dewey class and preserves an existing decimal and author suffix', async () => {
        const wrapper = mount(DeweyPicker, {
            props: { modelValue: '551.46 VER' },
            global: { mocks: { $t: key => key, t: key => key } }
        });

        await wrapper.find('button').trigger('click');
        await wrapper.findAll('.dewey-cls-btn')[5].trigger('click');
        expect(wrapper.vm.selectedClass).toBe(5);
        expect(wrapper.findAll('.dewey-picker-panel button')).toHaveLength(20);

        const subdivision = wrapper.findAll('.dewey-picker-panel button')[10];
        await subdivision.trigger('click');
        expect(wrapper.emitted('update:modelValue')).toContainEqual(['500.46 VER']);
        expect(wrapper.vm.open).toBe(false);
    });

    it.each([
        ['', '500.'],
        ['VER', '500 VER'],
        ['551', '500.']
    ])('inserts class %s while preserving the input form', async (current, expected) => {
        const wrapper = mount(DeweyPicker, {
            props: { modelValue: current },
            global: { mocks: { $t: key => key, t: key => key } }
        });
        wrapper.vm.insert('500');
        expect(wrapper.emitted('update:modelValue')).toContainEqual([expected]);
    });

    it('falls back to defaults for malformed colors and ignores invalid Dewey input', () => {
        const wrapper = mount(DeweyPicker, {
            props: { modelValue: 'ABC', colors: ['#fff'], enabled: true },
            global: { mocks: { $t: key => key, t: key => key } }
        });

        expect(wrapper.vm.badgeText).toBe('?');
        expect(wrapper.vm.classButtons).toHaveLength(10);
        expect(wrapper.vm.badgeStyle.background).toBe('transparent');
    });

    it('closes the picker on an outside click', async () => {
        const wrapper = mount(DeweyPicker, {
            props: { modelValue: '840' },
            global: { mocks: { $t: key => key, t: key => key } }
        });
        await wrapper.find('button').trigger('click');
        expect(wrapper.vm.open).toBe(true);
        document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        expect(wrapper.vm.open).toBe(false);
    });
});
