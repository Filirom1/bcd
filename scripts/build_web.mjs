import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");

const srcWebDir = path.join(projectRoot, "src", "bcd_web_vue");
const buildDir = path.join(projectRoot, "build", "web");
const tempHtmlPath = path.join(srcWebDir, "index.html");
const shellHtmlPath = path.join(srcWebDir, "templates", "spa-shell.html");
const temporaryEntryMarker = "<!-- BCD_VITE_TEMP_ENTRY -->";
const existingHtml = fs.existsSync(tempHtmlPath) ? fs.readFileSync(tempHtmlPath, "utf-8") : null;
const originalHtml = existingHtml?.includes(temporaryEntryMarker) ? null : existingHtml;

function cleanDir(dirPath) {
    if (fs.existsSync(dirPath)) {
        fs.rmSync(dirPath, { recursive: true, force: true });
    }
    fs.mkdirSync(dirPath, { recursive: true });
}

function copyRecursiveSync(src, dest) {
    const exists = fs.existsSync(src);
    const stats = exists && fs.statSync(src);
    const isDirectory = exists && stats.isDirectory();
    if (isDirectory) {
        if (!fs.existsSync(dest)) {
            fs.mkdirSync(dest, { recursive: true });
        }
        fs.readdirSync(src).forEach((childItemName) => {
            copyRecursiveSync(path.join(src, childItemName), path.join(dest, childItemName));
        });
    } else {
        fs.copyFileSync(src, dest);
    }
}

try {
    console.log("=== BCD Web UI Production Build ===");

    // 1. Clean build directory
    console.log(`Cleaning output directory: ${buildDir}`);
    cleanDir(buildDir);

    // 2. Prepare temporary entry HTML
    console.log(`Generating temporary index.html from shell template...`);
    if (!fs.existsSync(shellHtmlPath)) {
        throw new Error(`Shell template not found at ${shellHtmlPath}`);
    }
    let shellHtml = fs.readFileSync(shellHtmlPath, "utf-8");

    // Replace the placeholders with production script entries
    // Head assets placeholder is deleted because Vite manages head styling injection automatically
    let tempHtml = `${temporaryEntryMarker}\n${shellHtml.replace("<!-- BCD_HEAD_ASSETS -->", "")}`;
    tempHtml = tempHtml.replace(
        "<!-- BCD_BODY_ASSETS -->",
        '<script type="module" src="/js/production-entry.js"></script>'
    );

    fs.writeFileSync(tempHtmlPath, tempHtml, "utf-8");

    // 3. Run Vite build
    console.log("Running Vite compiler...");
    const cmd = "npx --no-install vite build";
    execSync(cmd, { cwd: projectRoot, stdio: "inherit" });

    // 4. Verify Vite output
    const outputHtmlPath = path.join(buildDir, "index.html");
    const manifestPath = path.join(buildDir, ".vite", "manifest.json");

    if (!fs.existsSync(outputHtmlPath)) {
        throw new Error(`Vite build failed to produce index.html at ${outputHtmlPath}`);
    }
    if (!fs.existsSync(manifestPath)) {
        throw new Error(`Vite build failed to produce manifest at ${manifestPath}`);
    }

    // 5. Copy locales recursively
    const srcLocales = path.join(srcWebDir, "locales");
    const destLocales = path.join(buildDir, "locales");
    console.log(`Copying locales from ${srcLocales} to ${destLocales}...`);
    copyRecursiveSync(srcLocales, destLocales);

    // 6. Copy favicons
    console.log("Copying favicons...");
    const favicons = ["favicon.ico", "favicon.png", "favicon.svg"];
    for (const fav of favicons) {
        const srcFav = path.join(srcWebDir, fav);
        if (fs.existsSync(srcFav)) {
            fs.copyFileSync(srcFav, path.join(buildDir, fav));
        }
    }

    console.log("🟢 Build completed successfully!");
} catch (error) {
    console.error("🔴 Build failed with error:");
    console.error(error.message);
    process.exit(1);
} finally {
    // 7. Restore a pre-existing source entry, otherwise remove our temporary file.
    if (originalHtml !== null) {
        fs.writeFileSync(tempHtmlPath, originalHtml);
    } else if (fs.existsSync(tempHtmlPath)) {
        console.log("Cleaning up temporary files...");
        fs.unlinkSync(tempHtmlPath);
    }
}
