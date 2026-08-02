import { defineConfig } from "vite";
import path from "path";

const rootDir = import.meta.dirname;

export default defineConfig({
  // Root directory is the folder containing our Web UI source code
  root: "src/bcd_web_vue",

  // Base public path for all assets - FastAPI serves static assets under /static/
  base: "/static/",

  resolve: {
    alias: {
      // Force Vite to use the Vue build with the runtime template compiler,
      // since our ESM modules define components using runtime 'template' strings.
      vue: "vue/dist/vue.esm-browser.prod.js",
    },
  },

  define: {
    // Vue 3 Feature Flags required by the ESM browser build
    __VUE_OPTIONS_API__: true,
    __VUE_PROD_DEVTOOLS__: false,
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: false,
  },

  build: {
    // Relative to root "src/bcd_web_vue", so output is in root "build/web"
    outDir: "../../build/web",
    emptyOutDir: true,
    manifest: true,
    assetsDir: "assets",
    sourcemap: false,
    target: "es2018",
    minify: "oxc",

    rollupOptions: {
      input: {
        main: path.resolve(rootDir, "src/bcd_web_vue/index.html"),
      },
    },
  },
});
