import { describe, expect, it, vi, afterEach } from 'vitest';
import { ref } from 'vue';
import { useDebouncedAction } from '../../../src/bcd_web_vue/js/composables/useDebouncedAction.js';

afterEach(() => {
    vi.useRealTimers();
});

describe('useDebouncedAction', () => {
    it('should debounce function calls and call with correct arguments', () => {
        vi.useFakeTimers();
        const action = vi.fn();
        const debounced = useDebouncedAction(action, 100);

        debounced('test1', 123);
        expect(action).not.toHaveBeenCalled();

        vi.advanceTimersByTime(50);
        expect(action).not.toHaveBeenCalled();

        debounced('test2', 456);
        vi.advanceTimersByTime(50);
        expect(action).not.toHaveBeenCalled();

        vi.advanceTimersByTime(50);
        expect(action).toHaveBeenCalledTimes(1);
        expect(action).toHaveBeenCalledWith('test2', 456);
    });

    it('should cancel pending execution', () => {
        vi.useFakeTimers();
        const action = vi.fn();
        const debounced = useDebouncedAction(action, 100);

        debounced('test');
        debounced.cancel();

        vi.advanceTimersByTime(100);
        expect(action).not.toHaveBeenCalled();
    });

    it('should flush pending execution immediately', () => {
        vi.useFakeTimers();
        const action = vi.fn();
        const debounced = useDebouncedAction(action, 100);

        debounced('test');
        debounced.flush();

        expect(action).toHaveBeenCalledTimes(1);
        expect(action).toHaveBeenCalledWith('test');

        vi.advanceTimersByTime(100);
        expect(action).toHaveBeenCalledTimes(1); // not run again
    });

    it('should support Ref delay', () => {
        vi.useFakeTimers();
        const action = vi.fn();
        const delayRef = ref(200);
        const debounced = useDebouncedAction(action, delayRef);

        debounced('test');
        vi.advanceTimersByTime(150);
        expect(action).not.toHaveBeenCalled();

        vi.advanceTimersByTime(50);
        expect(action).toHaveBeenCalledTimes(1);
    });
});
