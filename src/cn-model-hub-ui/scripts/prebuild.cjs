#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const rootDir = path.join(__dirname, "..", "..", "..");
const publicDir = path.join(__dirname, "..", "public");
const docsSourceDir = path.join(rootDir, "docs");
const docsPublicDir = path.join(publicDir, "documentation");
const imagesPublicDir = path.join(publicDir, "images");

function resetDir(dir) {
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
}

function copyFile(source, dest) {
  if (!fs.existsSync(source)) {
    console.warn(`Skip missing file: ${source}`);
    return;
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(source, dest);
  console.log(`Copied ${path.relative(rootDir, source)} -> ${path.relative(rootDir, dest)}`);
}

function copyMarkdownDir(sourceDir, destDir) {
  if (!fs.existsSync(sourceDir)) {
    console.warn(`Docs directory not found: ${sourceDir}`);
    return;
  }

  fs.mkdirSync(destDir, { recursive: true });
  const entries = fs.readdirSync(sourceDir, { withFileTypes: true });
  const mdFiles = [];

  for (const entry of entries) {
    const sourcePath = path.join(sourceDir, entry.name);
    const destPath = path.join(destDir, entry.name);
    if (entry.isDirectory()) {
      copyMarkdownDir(sourcePath, destPath);
      continue;
    }
    if (entry.isFile() && entry.name.endsWith(".md")) {
      copyFile(sourcePath, destPath);
      mdFiles.push(entry.name);
    }
  }

  if (mdFiles.length > 0) {
    fs.writeFileSync(path.join(destDir, ".manifest.json"), JSON.stringify(mdFiles, null, 2));
  }
}

function main() {
  console.log("Preparing cn_model_hub public assets...");
  resetDir(docsPublicDir);
  fs.mkdirSync(imagesPublicDir, { recursive: true });

  copyMarkdownDir(docsSourceDir, docsPublicDir);

  const logoFiles = [
    ["images/logo-square.png", "images/logo-square.png"],
    ["images/logo-banner.svg", "images/logo-banner.svg"],
    ["images/logo-banner-dark.svg", "images/logo-banner-dark.svg"],
    ["images/favicon-32x32.png", "favicon-32x32.png"],
    ["images/favicon-16x16.png", "favicon-16x16.png"],
    ["images/apple-touch-icon.png", "apple-touch-icon.png"],
  ];
  for (const [source, dest] of logoFiles) {
    copyFile(path.join(rootDir, source), path.join(publicDir, dest));
  }
  console.log("Public assets ready.");
}

main();
