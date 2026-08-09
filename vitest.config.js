import { defineConfig } from 'vitest/config';

export default defineConfig({
    test: {
        include: ['tests/js/**/*.test.js'],
        environment: 'jsdom',
        setupFiles: ['tests/js/setup/globals.js'],
        clearMocks: true,
        restoreMocks: true,
        coverage: {
            provider: 'v8',
            all: true,
            reportsDirectory: 'coverage-js',
            reporter: ['text', 'lcov', 'html', 'json-summary'],
            include: ['src/bcd_web_vue/js/**/*.js'],
            // Vendor assets are executed by the browser but are not BCD source.
            // The full application source is included so the baseline cannot hide
            // untested components and pages.
            exclude: ['**/vendor/**']
        }
    }
});
