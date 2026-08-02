import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const buildDir = path.join(projectRoot, "build", "web");

console.log("=== BCD Web Build Verification ===");

try {
    // 1. Check basic existence
    const htmlPath = path.join(buildDir, "index.html");
    if (!fs.existsSync(htmlPath)) {
        throw new Error(`index.html is missing at ${htmlPath}`);
    }

    const manifestPath = path.join(buildDir, ".vite", "manifest.json");
    if (!fs.existsSync(manifestPath)) {
        throw new Error(`Vite manifest.json is missing at ${manifestPath}`);
    }

    // 2. Read index.html content
    const htmlContent = fs.readFileSync(htmlPath, "utf-8");

    // 3. Prohibit dev / vendor / external assets
    const forbiddenPatterns = [
        { pattern: "/node_modules/", name: "Node modules" },
        { pattern: "/static/vendor/", name: "Vendored static assets" },
        { pattern: "js/app.js", name: "Direct app.js reference" },
        { pattern: "http://", name: "Unsecure CDN / external URL" },
        { pattern: "https://", name: "Secure CDN / external URL" },
    ];

    for (const { pattern, name } of forbiddenPatterns) {
        if (htmlContent.includes(pattern)) {
            throw new Error(`Build contains forbidden reference to ${name} ('${pattern}') inside index.html`);
        }
    }

    // 4. Verify locale files exist
    const locales = ["fr.json", "en.json"];
    for (const locale of locales) {
        const localePath = path.join(buildDir, "locales", locale);
        if (!fs.existsSync(localePath)) {
            throw new Error(`Locale file is missing at ${localePath}`);
        }
    }

    // 5. Verify favicons exist
    const faviconPath = path.join(buildDir, "favicon.svg");
    if (!fs.existsSync(faviconPath)) {
        throw new Error(`Favicon is missing at ${faviconPath}`);
    }

    // 6. Verify that referenced assets inside index.html exist on disk
    // Find all links/scripts pointing to /static/assets/
    const assetRegex = /\/static\/assets\/([^"'\s>]+)/g;
    let match;
    let checkedAssetsCount = 0;

    while ((match = assetRegex.exec(htmlContent)) !== null) {
        const assetName = match[1];
        const assetOnDiskPath = path.join(buildDir, "assets", assetName);
        if (!fs.existsSync(assetOnDiskPath)) {
            throw new Error(`HTML references asset '/static/assets/${assetName}', but it is missing on disk at ${assetOnDiskPath}`);
        }
        checkedAssetsCount++;
    }

    console.log(`Verified ${checkedAssetsCount} referenced hashed assets successfully.`);
    console.log("🟢 Web UI production build structure is 100% valid!");
} catch (error) {
    console.error("🔴 Verification failed:");
    console.error(error.message);
    process.exit(1);
}
