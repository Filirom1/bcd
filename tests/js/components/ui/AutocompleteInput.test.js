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

    it('shows no-results and error states without leaving stale suggestions', async () => {
        fetchSpy.mockResolvedValueOnce([]);
        const empty = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        await empty.get('input').setValue('zz');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(empty.vm.showNoResults).toBe(true);
        expect(empty.text()).toContain('autocomplete.no_results');

        fetchSpy.mockRejectedValueOnce(new Error('offline'));
        const failed = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        await failed.get('input').setValue('zz');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(failed.vm.error).toBe('autocomplete.error');
        // Failed requests keep the dropdown closed; the reactive error is still exposed to the parent.
        expect(failed.vm.showDropdown).toBe(false);
    });

    it('does not search below the minimum length and syncs an initial external value', async () => {
        const wrapper = mount(AutocompleteInput, {
            props: { modelValue: 'initial', fetchResults: fetchSpy, formatResult, minChars: 3 },
            global: { mocks: { $t: key => key } }
        });
        expect(wrapper.get('input').element.value).toBe('initial');
        await wrapper.get('input').setValue('ab');
        vi.advanceTimersByTime(500);
        expect(fetchSpy).not.toHaveBeenCalled();

        await wrapper.setProps({ modelValue: 'external' });
        expect(wrapper.vm.inputValue).toBe('external');
    });

    it('selects a result, submits raw input, and closes on Escape', async () => {
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult, autoSelectFirst: false },
            global: { mocks: { $t: key => key } }
        });
        await wrapper.get('input').setValue('ha');
        vi.advanceTimersByTime(300);
        await flushPromises();

        await wrapper.get('.autocomplete-item').trigger('click');
        expect(wrapper.emitted('select')).toEqual([[{ id: 1, name: 'Result 1' }]]);
        expect(wrapper.vm.showDropdown).toBe(false);

        wrapper.vm.showDropdown = true;
        wrapper.vm.results = [{ id: 3, name: 'Other' }];
        await wrapper.get('input').trigger('keydown', { key: 'Escape' });
        expect(wrapper.vm.showDropdown).toBe(false);

        wrapper.vm.handleSubmit();
        expect(wrapper.emitted('submit')).toBeTruthy();
    });

    it('ignores AbortError without displaying an error', async () => {
        fetchSpy.mockRejectedValueOnce(Object.assign(new Error('cancelled'), { name: 'AbortError' }));
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        await wrapper.get('input').setValue('ab');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(wrapper.vm.error).toBe(null);
        expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('handles null, malformed and empty result collections as no results', async () => {
        fetchSpy.mockResolvedValueOnce(null).mockResolvedValueOnce({ results: [] }).mockResolvedValueOnce([]);
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        await wrapper.get('input').setValue('ab');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(wrapper.vm.results).toEqual([]);
        expect(wrapper.vm.showNoResults).toBe(true);
        expect(wrapper.text()).toContain('autocomplete.no_results');
    });

    it('uses or skips autoSelectFirst and submits raw text according to the prop', async () => {
        const automatic = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult, autoSelectFirst: true },
            global: { mocks: { $t: key => key } }
        });
        await automatic.get('input').setValue('ab');
        vi.advanceTimersByTime(300);
        await flushPromises();
        await automatic.get('input').trigger('keydown', { key: 'Enter' });
        expect(automatic.emitted('select')).toEqual([[{ id: 1, name: 'Result 1' }]]);

        const manual = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult, autoSelectFirst: false },
            global: { mocks: { $t: key => key } }
        });
        await manual.get('input').setValue('manual');
        vi.advanceTimersByTime(300);
        await flushPromises();
        await manual.get('input').trigger('keydown', { key: 'Enter' });
        expect(manual.emitted('select')).toBeUndefined();
        expect(manual.emitted('submit')).toEqual([['manual']]);
    });

    it('handles Enter with no dropdown and keeps arrow selection at both limits', async () => {
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        await wrapper.get('input').trigger('keydown', { key: 'Enter' });
        expect(wrapper.emitted('submit')).toEqual([['']]);

        wrapper.vm.results = [{ id: 1 }, { id: 2 }];
        wrapper.vm.showDropdown = true;
        await wrapper.get('input').trigger('keydown', { key: 'ArrowUp' });
        expect(wrapper.vm.selectedIndex).toBe(-1);
        await wrapper.get('input').trigger('keydown', { key: 'ArrowDown' });
        await wrapper.get('input').trigger('keydown', { key: 'ArrowDown' });
        await wrapper.get('input').trigger('keydown', { key: 'ArrowDown' });
        expect(wrapper.vm.selectedIndex).toBe(1);
    });

    it('cancels a loading request with Escape and closes on an outside click', async () => {
        let resolveRequest;
        fetchSpy.mockImplementationOnce(() => new Promise(resolve => { resolveRequest = resolve; }));
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        await wrapper.get('input').setValue('ab');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(wrapper.vm.loading).toBe(true);
        wrapper.vm.showDropdown = true;
        await wrapper.get('input').trigger('keydown', { key: 'Escape' });
        expect(wrapper.vm.showDropdown).toBe(false);
        expect(wrapper.vm.loading).toBe(true);
        resolveRequest([]);
        await flushPromises();

        wrapper.vm.showDropdown = true;
        document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        expect(wrapper.vm.showDropdown).toBe(false);
    });

    it('ignores an obsolete response that resolves after a newer query', async () => {
        const requests = new Map();
        fetchSpy.mockImplementation(query => new Promise(resolve => {
            requests.set(query, resolve);
        }));
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });

        await wrapper.get('input').setValue('abc');
        vi.advanceTimersByTime(300);
        await flushPromises();
        await wrapper.get('input').setValue('abcd');
        vi.advanceTimersByTime(300);
        await flushPromises();

        expect(fetchSpy).toHaveBeenCalledTimes(2);
        requests.get('abcd')([{ id: 'new', name: 'New result' }]);
        await flushPromises();
        expect(wrapper.vm.results).toEqual([{ id: 'new', name: 'New result' }]);

        requests.get('abc')([{ id: 'old', name: 'Old result' }]);
        await flushPromises();
        expect(wrapper.vm.results).toEqual([{ id: 'new', name: 'New result' }]);
    });

    it('does not accept keyboard input on a disabled component', async () => {
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult, disabled: true },
            global: { mocks: { $t: key => key } }
        });
        await wrapper.get('input').trigger('keydown', { key: 'Enter' });
        expect(fetchSpy).not.toHaveBeenCalled();
        expect(wrapper.emitted('update:modelValue')).toBeUndefined();
        expect(wrapper.emitted('submit')).toBeUndefined();
    });

    it('does not use scanner submit for a slow Enter and ignores a late response after close', async () => {
        vi.useRealTimers();
        let resolveRequest;
        fetchSpy.mockImplementation(() => new Promise(resolve => { resolveRequest = resolve; }));
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        wrapper.vm.handleInput({ target: { value: 'abc' } });
        await new Promise(resolve => setTimeout(resolve, 350));
        expect(fetchSpy).toHaveBeenCalledTimes(1);
        wrapper.vm.showDropdown = true;
        wrapper.vm.results = [{ id: 1, name: 'Suggestion' }];
        await new Promise(resolve => setTimeout(resolve, 210));
        wrapper.vm.handleKeydown({ key: 'Enter', preventDefault: vi.fn() });
        expect(wrapper.emitted('select')).toEqual([[{ id: 1, name: 'Suggestion' }]]);
        expect(wrapper.emitted('submit')).toBeUndefined();
        resolveRequest([{ id: 2, name: 'Late result' }]);
        await flushPromises();
        expect(wrapper.vm.showDropdown).toBe(false);
        expect(wrapper.vm.results).toEqual([{ id: 1, name: 'Suggestion' }]);
    });

    it('reflects disabled state and external model changes while a request is pending', async () => {
        let resolveRequest;
        fetchSpy.mockImplementationOnce(() => new Promise(resolve => { resolveRequest = resolve; }));
        const wrapper = mount(AutocompleteInput, {
            props: { modelValue: 'old', fetchResults: fetchSpy, formatResult, disabled: true },
            global: { mocks: { $t: key => key } }
        });
        expect(wrapper.get('input').attributes('disabled')).toBeDefined();
        wrapper.vm.handleInput({ target: { value: 'old query' } });
        vi.advanceTimersByTime(300);
        await flushPromises();
        await wrapper.setProps({ modelValue: 'new' });
        expect(wrapper.vm.inputValue).toBe('new');
        wrapper.vm.showDropdown = true;
        wrapper.vm.handleKeydown({ key: 'Escape', preventDefault: vi.fn() });
        expect(wrapper.vm.showDropdown).toBe(false);
        resolveRequest([]);
        await flushPromises();
    });

    it('focuses the real input when focusInput is requested', async () => {
        const wrapper = mount(AutocompleteInput, {
            attachTo: document.body,
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });

        await wrapper.vm.focusInput();

        expect(document.activeElement).toBe(wrapper.get('input').element);
    });

    it('ignores a response that arrives after the component is unmounted', async () => {
        let resolveRequest;
        fetchSpy.mockImplementationOnce(() => new Promise(resolve => { resolveRequest = resolve; }));
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        await wrapper.get('input').setValue('late');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(wrapper.vm.loading).toBe(true);

        wrapper.unmount();
        resolveRequest([{ id: 9, name: 'Too late' }]);
        await flushPromises();

        expect(wrapper.vm.results).toEqual([]);
        expect(wrapper.vm.showDropdown).toBe(false);
    });

    it('closes a rendered dropdown when clicking outside its container', async () => {
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        await wrapper.get('input').setValue('book');
        vi.advanceTimersByTime(300);
        await flushPromises();

        expect(wrapper.find('[role="listbox"]').exists()).toBe(true);
        document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await wrapper.vm.$nextTick();
        expect(wrapper.find('[role="listbox"]').exists()).toBe(false);
    });

    it('supports keyboard selection when a result has incomplete fields', async () => {
        fetchSpy.mockResolvedValueOnce([{ id: 1 }, { id: 2, name: 'Complete' }]);
        const safeFormat = item => `<b>${item?.name || 'Unnamed'}</b>`;
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult: safeFormat, autoSelectFirst: false },
            global: { mocks: { $t: key => key } }
        });
        await wrapper.get('input').setValue('part');
        vi.advanceTimersByTime(300);
        await flushPromises();

        await wrapper.get('input').trigger('keydown', { key: 'ArrowDown' });
        await wrapper.get('input').trigger('keydown', { key: 'Enter' });

        expect(wrapper.emitted('select')).toEqual([[{ id: 1 }]]);
        expect(wrapper.find('[role="listbox"]').exists()).toBe(false);
    });

    it('keeps the dropdown open for inside clicks and trims scanner keystroke history', async () => {
        const wrapper = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        for (const value of ['a', 'ab', 'abc', 'abcd', 'abcde', 'abcdef']) {
            wrapper.vm.handleInput({ target: { value } });
        }
        expect(wrapper.vm.inputValue).toBe('abcdef');
        vi.advanceTimersByTime(300);
        await flushPromises();
        expect(wrapper.find('[role="listbox"]').exists()).toBe(true);

        await wrapper.get('input').trigger('click');
        expect(wrapper.find('[role="listbox"]').exists()).toBe(true);

        const slowScanner = mount(AutocompleteInput, {
            props: { fetchResults: fetchSpy, formatResult },
            global: { mocks: { $t: key => key } }
        });
        slowScanner.vm.handleInput({ target: { value: 'manual' } });
        slowScanner.vm.showDropdown = true;
        slowScanner.vm.results = [{ id: 3, name: 'Manual result' }];
        slowScanner.vm.handleKeydown({ key: 'Enter', preventDefault: vi.fn() });
        expect(slowScanner.emitted('select')).toEqual([[{ id: 3, name: 'Manual result' }]]);

        slowScanner.vm.showDropdown = true;
        slowScanner.vm.results = [{ id: 4, name: 'No scroll node' }];
        slowScanner.vm.dropdownRef = null;
        slowScanner.vm.handleKeydown({ key: 'ArrowDown', preventDefault: vi.fn() });
        await slowScanner.vm.$nextTick();
        expect(slowScanner.vm.selectedIndex).toBe(0);
    });
});
