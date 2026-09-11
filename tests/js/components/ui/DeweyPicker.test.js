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
});
