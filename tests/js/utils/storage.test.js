import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
    getItem,
    setItem,
    removeItem,
    getJSON,
    setJSON,
    clearStorage
} from '../../../src/bcd_web_vue/js/utils/storage.js';

beforeEach(() => {
    localStorage.clear();
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
});

afterEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
});

describe('localStorage Utility Adapter', () => {
    it('sets and gets raw string values with prefix', () => {
        setItem('test_key', 'hello');
        expect(localStorage.getItem('bcd_test_key')).toBe('hello');
        expect(getItem('test_key')).toBe('hello');
        expect(getItem('non_existent', 'fallback')).toBe('fallback');
    });

    it('removes keys with prefix', () => {
        setItem('test_key', 'hello');
        removeItem('test_key');
        expect(localStorage.getItem('bcd_test_key')).toBeNull();
        expect(getItem('test_key')).toBeNull();
    });

    it('serializes and deserializes JSON correctly', () => {
        const obj = { name: 'BCD', active: true };
        setJSON('config', obj);
        expect(localStorage.getItem('bcd_config')).toBe(JSON.stringify(obj));
        expect(getJSON('config')).toEqual(obj);
    });

    it('returns fallback and logs error if JSON parsing fails', () => {
        localStorage.setItem('bcd_bad_json', '{bad}');
        const fallback = { empty: true };
        expect(getJSON('bad_json', fallback)).toEqual(fallback);
        expect(console.error).toHaveBeenCalled();
    });

    it('clears only bcd prefixed keys', () => {
        localStorage.setItem('bcd_one', '1');
        localStorage.setItem('bcd_two', '2');
        localStorage.setItem('other_app', 'keep');

        clearStorage();

        expect(localStorage.getItem('bcd_one')).toBeNull();
        expect(localStorage.getItem('bcd_two')).toBeNull();
        expect(localStorage.getItem('other_app')).toBe('keep');
    });

    it('safely handles browser blocking exceptions', () => {
        vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
            throw new Error('SecurityError: The operation is insecure.');
        });
        vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
            throw new Error('SecurityError: The operation is insecure.');
        });

        expect(getItem('test_key', 'fallback')).toBe('fallback');
        expect(() => setItem('test_key', 'value')).not.toThrow();
        expect(console.warn).toHaveBeenCalled();
    });
});
