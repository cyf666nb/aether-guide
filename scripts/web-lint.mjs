import { readdir, readFile } from "node:fs/promises";
import path from "node:path";

const target = process.argv[2] ?? ".";
const root = path.resolve(target);
const extensions = new Set([".css", ".ts", ".tsx", ".js", ".jsx", ".html"]);
const ignored = new Set(["node_modules", ".next", "out", "dist"]);

const bannedPatterns = [
  { pattern: /\b(?:blue|purple|slate|zinc|neutral|gray|indigo|pink)-[1-9]00\b/, label: "default Tailwind color token" },
  { pattern: /from-blue-500|to-purple-600/, label: "generic blue/purple gradient" },
  { pattern: /rounded-2xl|rounded-3xl|shadow-lg|shadow-md/, label: "generic large radius/shadow utility" },
  { pattern: /Powered by AI/i, label: "generic AI badge copy" },
  { pattern: /🚀|✨|🎉/, label: "generic decorative emoji" },
  { pattern: /Network failed|is undefined|was undefined/i, label: "raw user-facing failure text" }
];

const failures = [];

async function walk(dir) {
  const entries = await readdir(dir, { withFileTypes: true });
  for (const entry of entries) {
    if (ignored.has(entry.name)) continue;
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      await walk(fullPath);
      continue;
    }
    if (!extensions.has(path.extname(entry.name))) continue;
    const text = await readFile(fullPath, "utf8");
    for (const check of bannedPatterns) {
      if (check.pattern.test(text)) {
        failures.push(`${path.relative(process.cwd(), fullPath)}: ${check.label}`);
      }
    }
  }
}

await walk(root);

if (failures.length) {
  console.error("Frontend visual lint failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Frontend visual lint passed for ${path.relative(process.cwd(), root) || "."}`);

