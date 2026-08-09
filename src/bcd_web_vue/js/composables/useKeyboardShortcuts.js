// @ts-check
/**
 * Keyboard Shortcuts Composable
 *
 * Provides two types of shortcuts:
 *  - Navigation: Alt+F1-F9 to jump between pages (shown in sidebar when Alt held)
 *  - Admin actions: Alt+Letter to trigger per-page operations (shown in admin dropdown)
 *
 * altHeld: reactive bool, true while the Alt key is physically held.
 * This is exported directly so any component can import it to show/hide hints.
 */

const { ref, onMounted, onUnmounted } = Vue;

// ─── Module-level singletons ──────────────────────────────────────────────────

export const altHeld = ref(false);

// Map of uppercase letter → callback, registered by whichever page is active
const adminCallbacks = new Map();

let listenerCount = 0;

// Navigation shortcuts: Alt+Letter.
// Letters are matched case-insensitively via event.key, which is layout-independent
// for alphabetic keys (pressing 'A' on any layout gives event.key = 'a').
// These letters must not overlap with admin shortcuts (N, I, X, E, M, P, K).
const NAV_SHORTCUTS = [
    { key: 'A', route: '/checkout' },         // Alt+A — Accueil
    { key: 'R', route: '/return' },           // Alt+R — Retour
    { key: 'C', route: '/catalog' },          // Alt+C — Catalogue
    { key: 'L', route: '/borrowers' },        // Alt+L — Lecteurs
    { key: 'S', route: '/classes' },          // Alt+S — claSSes
    { key: 'B', route: '/reports/overdue' },  // Alt+B — Bilan
    { key: 'O', route: '/settings' },         // Alt+O — Options
    { key: 'G', route: '/cataloging' },       // Alt+G — cataloGage (hidden from nav)
];

// ─── Event handlers ───────────────────────────────────────────────────────────

/**
 * @param {KeyboardEvent} event
 */
function onKeydown(event) {
    // Track whether Alt is physically held (for hint display in sidebar)
    if (event.key === 'Alt') {
        altHeld.value = true;
    }

    // From here we only care about Alt+something combinations
    if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;

    // Navigation shortcuts: Alt+Letter
    const navMatch = NAV_SHORTCUTS.find(s => s.key === event.key.toUpperCase());
    if (navMatch) {
        event.preventDefault();
        window.location.hash = navMatch.route;
        return;
    }

    // Admin shortcuts: Alt+single letter
    if (/^[a-zA-Z]$/.test(event.key)) {
        const cb = adminCallbacks.get(event.key.toUpperCase());
        if (cb) {
            event.preventDefault();
            cb();
        }
    }
}

/**
 * @param {KeyboardEvent} event
 */
function onKeyup(event) {
    if (event.key === 'Alt') {
        altHeld.value = false;
    }
}

function onWindowBlur() {
    // Alt+Tab leaves the window with Alt still "down" — reset the state
    altHeld.value = false;
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Initialize the global keyboard shortcut system.
 * Call once from App.js — attaches document-level listeners immediately.
 */
export function useKeyboardShortcuts() {
    if (listenerCount === 0) {
        document.addEventListener('keydown', onKeydown);
        document.addEventListener('keyup', onKeyup);
        window.addEventListener('blur', onWindowBlur);
    }
    listenerCount++;

    onUnmounted(() => {
        listenerCount--;
        if (listenerCount === 0) {
            document.removeEventListener('keydown', onKeydown);
            document.removeEventListener('keyup', onKeyup);
            window.removeEventListener('blur', onWindowBlur);
        }
    });

    return { altHeld };
}

/**
 * Register admin keyboard shortcuts for the current page.
 * Automatically unregistered when the component unmounts.
 *
 * @param {Object} callbacks - Map of uppercase letter to handler, e.g. { I: handleImport }
 */
export function useAdminShortcuts(callbacks) {
    // Register in onMounted (not immediately) so the old page's onUnmounted
    // has already cleared its callbacks before we register the new ones.
    onMounted(() => {
        Object.entries(callbacks).forEach(([key, fn]) => {
            adminCallbacks.set(key.toUpperCase(), fn);
        });
    });

    onUnmounted(() => {
        Object.keys(callbacks).forEach(key => {
            adminCallbacks.delete(key.toUpperCase());
        });
    });
}
