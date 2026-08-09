/**
 * Control the lightweight Vue I18n contract installed by setup/globals.js.
 *
 * Use this only for component tests. Locale-file parity remains a separate
 * contract tested through the application translation files.
 */
export function setTestTranslator(translator) {
    globalThis.__testTranslate = translator;
}

export function resetTestTranslator() {
    globalThis.__testTranslate = key => key;
}
