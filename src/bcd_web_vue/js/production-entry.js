// Production Entry Point for Vite Build
// Exposes NPM libraries to globalThis for backward-compatibility with current ESM modules

// 1. Order of CSS imports matching original index.html exactly
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import "../css/main.css";
import "../css/loading.css";
import "../css/print-labels.css";

// Only the Bootstrap behaviors used by the UI are loaded. Modal markup is
// implemented in Vue; dropdowns and the help offcanvas use these modules.
import "bootstrap/js/dist/dropdown.js";
import "bootstrap/js/dist/offcanvas.js";

// 2. Import core libraries
import * as Vue from "vue";
import * as VueRouter from "vue-router";
import { createI18n, useI18n } from "vue-i18n";
// Feature-specific libraries are imported by the components that use them.
// Vite tree-shakes these imports and keeps route-specific code in lazy chunks.

// 3. Populate globalThis bridge BEFORE importing app.js
globalThis.Vue = Vue;
globalThis.VueRouter = VueRouter;
globalThis.VueI18n = { createI18n, useI18n };

// 4. Dynamically import app.js to ensure globals are registered first
import("./app.js").catch((err) => {
    console.error("Failed to load application modules:", err);
});
