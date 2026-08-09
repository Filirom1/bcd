import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { events } from '../../../src/bcd_web_vue/js/utils/events.js';

beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe('Event Bus Utility', () => {
    it('notifies subscribers of emitted events', () => {
        const callback1 = vi.fn();
        const callback2 = vi.fn();

        events.on('test-event', callback1);
        events.on('test-event', callback2);

        events.emit('test-event', 'payload', 123);

        expect(callback1).toHaveBeenCalledWith('payload', 123);
        expect(callback2).toHaveBeenCalledWith('payload', 123);
    });

    it('supports unsubscribing via unsubscribe function', () => {
        const callback = vi.fn();
        const unsubscribe = events.on('test-event', callback);

        unsubscribe();
        events.emit('test-event');

        expect(callback).not.toHaveBeenCalled();
    });

    it('supports explicit off()', () => {
        const callback = vi.fn();
        events.on('test-event', callback);
        events.off('test-event', callback);

        events.emit('test-event');

        expect(callback).not.toHaveBeenCalled();
    });

    it('isolates errors in listeners so other listeners still run', () => {
        const badCallback = vi.fn().mockImplementation(() => {
            throw new Error('Boom');
        });
        const goodCallback = vi.fn();

        events.on('risky-event', badCallback);
        events.on('risky-event', goodCallback);

        events.emit('risky-event');

        expect(badCallback).toHaveBeenCalled();
        expect(goodCallback).toHaveBeenCalled();
        expect(console.error).toHaveBeenCalled();
    });
});
