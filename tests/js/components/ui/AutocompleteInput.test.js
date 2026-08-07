import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import AutocompleteInput from '../../../../src/bcd_web_vue/js/components/ui/AutocompleteInput.js';

describe('AutocompleteInput', () => {
    let fetchSpy;

    beforeEach(() => {
        vi.useFakeTimers();
        fetchSpy = vi.fn().mockResolvedValue([
            { id: 1, name: 'Result 1' },
            { id: 2, name: 'Result 2' }
        ]);
        // Stub scrollIntoView which doesn't exist in JSDOM
        Element.prototype.scrollIntoView = vi.fn();
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    const formatResult = (item) => `<b>${item.name}</b>`;

    it('debounces fetching results on user input', async () => {
        const wrapper = mount(AutocompleteInput, {
            props: {
                modelValue: '',
                fetchResults: fetchSpy,
                formatResult,
                debounceMs: 300,
                minChars: 2
            },
            global: { mocks: { $t: key => key } }
        });

        // Type partial query
        await wrapper.get('input').setValue('ha');

        // Shorter than 300ms, should not have fetched yet
        vi.advanceTimersByTime(200);
        expect(fetchSpy).not.toHaveBeenCalled();

        // Pass the 300ms mark
        vi.advanceTimersByTime(100);
        expect(fetchSpy).toHaveBeenCalledWith('ha', expect.any(AbortSignal));

        await flushPromises();
        expect(wrapper.vm.results).toHaveLength(2);
        expect(wrapper.vm.showDropdown).toBe(true);
    });

    it('aborts the previous in-flight request when a new character is typed', async () => {
        const wrapper = mount(AutocompleteInput, {
            props: {
                modelValue: '',
                fetchResults: fetchSpy,
                formatResult
            },
            global: { mocks: { $t: key => key } }
        });

        await wrapper.get('input').setValue('ha');
        vi.advanceTimersByTime(300);

        const abortSpy = vi.spyOn(AbortController.prototype, 'abort');

        // Type another character to trigger a new query
        await wrapper.get('input').setValue('har');
        vi.advanceTimersByTime(300);

        expect(abortSpy).toHaveBeenCalled();
    });

    it('navigates search suggestions using ArrowDown, ArrowUp, and Enter keys', async () => {
        const wrapper = mount(AutocompleteInput, {
            props: {
                modelValue: '',
                fetchResults: fetchSpy,
                formatResult,
                autoSelectFirst: false
            },
            global: { mocks: { $t: key => key } }
        });

        await wrapper.get('input').setValue('ha');
        vi.advanceTimersByTime(300);
        await flushPromises();

        expect(wrapper.vm.showDropdown).toBe(true);
        expect(wrapper.vm.results).toHaveLength(2);
        expect(wrapper.vm.selectedIndex).toBe(-1);

        // ArrowDown -> select first result
        await wrapper.get('input').trigger('keydown', { key: 'ArrowDown' });
        expect(wrapper.vm.selectedIndex).toBe(0);

        // ArrowDown -> select second result
        await wrapper.get('input').trigger('keydown', { key: 'ArrowDown' });
        expect(wrapper.vm.selectedIndex).toBe(1);

        // ArrowUp -> back to first result
        await wrapper.get('input').trigger('keydown', { key: 'ArrowUp' });
        expect(wrapper.vm.selectedIndex).toBe(0);

        // Enter -> select first result
        await wrapper.get('input').trigger('keydown', { key: 'Enter' });
        expect(wrapper.emitted('select')).toEqual([[{ id: 1, name: 'Result 1' }]]);
    });

    it('bypasses autocomplete fetch when rapid keystrokes simulate barcode scanner input', async () => {
        vi.useRealTimers();

        const wrapper = mount(AutocompleteInput, {
            props: {
                modelValue: '',
                fetchResults: fetchSpy,
                formatResult
            },
            global: { mocks: { $t: key => key } }
        });

        // Mock Date.now to return progressive fast times (20ms increments)
        let mockTime = 1000;
        vi.spyOn(Date, 'now').mockImplementation(() => {
            mockTime += 20;
            return mockTime;
        });

        // Trigger manual handleInput calls simulating rapid typing
        wrapper.vm.handleInput({ target: { value: '9' } });
        wrapper.vm.handleInput({ target: { value: '97' } });
        wrapper.vm.handleInput({ target: { value: '978' } });
        wrapper.vm.handleInput({ target: { value: '9782070612758' } });

        await flushPromises();

        // Trigger keydown Enter directly on the VM
        wrapper.vm.handleKeydown({ key: 'Enter', preventDefault: () => {} });

        // Autocomplete should be bypassed on rapid input and submit the full code
        expect(wrapper.emitted('submit')).toEqual([['9782070612758']]);
    });

    it('supports multiple simultaneous instances with unique IDs', async () => {
        const wrapper1 = mount(AutocompleteInput, {
            props: {
                modelValue: '',
                fetchResults: fetchSpy,
                formatResult
            },
            global: { mocks: { $t: key => key } }
        });

        const wrapper2 = mount(AutocompleteInput, {
            props: {
                modelValue: '',
                fetchResults: fetchSpy,
                formatResult
            },
            global: { mocks: { $t: key => key } }
        });

        const id1 = wrapper1.vm.dropdownId;
        const id2 = wrapper2.vm.dropdownId;

        expect(id1).not.toBe(id2);
        expect(wrapper1.find('input').attributes('aria-controls')).toBe(undefined);

        // Open first dropdown
        await wrapper1.get('input').setValue('ha');
        vi.advanceTimersByTime(300);
        await flushPromises();

        expect(wrapper1.vm.showDropdown).toBe(true);
        expect(wrapper2.vm.showDropdown).toBe(false);
        expect(wrapper1.find('input').attributes('aria-controls')).toBe(id1);
    });
});
