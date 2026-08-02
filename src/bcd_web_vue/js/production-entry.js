// Production Entry Point for Vite Build
// Exposes NPM libraries to globalThis for backward-compatibility with current ESM modules

// 1. Order of CSS imports matching original index.html exactly
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap-icons/font/bootstrap-icons.css";
import "../css/main.css";
import "../css/loading.css";
import "../css/print-labels.css";

// Import Bootstrap JS bundle (includes Popper.js, required for offcanvas help panel and dropdowns)
import "bootstrap/dist/js/bootstrap.bundle.min.js";

// 2. Import core libraries
import * as Vue from "vue";
import * as VueRouter from "vue-router";
import { createI18n, useI18n } from "vue-i18n";
import { marked } from "marked";
import JsBarcode from "jsbarcode";
import { Chart } from "chart.js/auto"; // Use auto registration for full features

// 3. Populate globalThis bridge BEFORE importing app.js
globalThis.Vue = Vue;
globalThis.VueRouter = VueRouter;
globalThis.VueI18n = { createI18n, useI18n };
globalThis.marked = marked;
globalThis.JsBarcode = JsBarcode;
globalThis.Chart = Chart;

// 4. Dynamically import app.js to ensure globals are registered first
import("./app.js").catch((err) => {
    console.error("Failed to load application modules:", err);
});
