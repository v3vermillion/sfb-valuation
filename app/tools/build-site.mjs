// build-site.mjs — copy public/ into dist/, stamp the service worker with a content hash + precache list,
// and inject deploy-time config (the live-check Worker URL) into index.html. dist/db is left alone.
//   node tools/build-site.mjs [--live https://sfb-pipeline.example.workers.dev] [--out dist]
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const APP = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => (a.startsWith("--") ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true] : [])).filter((x) => x.length));
const OUT = path.resolve(APP, args.out || "dist");
const LIVE = (args.live ?? process.env.LIVE_CHECK_URL ?? "").toString().trim();
const PUB = path.join(APP, "public");

function walk(dir, base = dir, acc = []) {
  for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, ent.name);
    if (ent.isDirectory()) walk(p, base, acc); else acc.push(path.relative(base, p).split(path.sep).join("/"));
  }
  return acc;
}

const files = walk(PUB).sort();
fs.mkdirSync(OUT, { recursive: true });
const hash = crypto.createHash("sha256");
for (const f of files) {
  const src = path.join(PUB, f), dst = path.join(OUT, f);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.copyFileSync(src, dst);
  if (f !== "sw.js") hash.update(f).update(fs.readFileSync(src));
}
hash.update(LIVE);
const BUILD = hash.digest("hex").slice(0, 10);

// index.html: config stamps
const idx = path.join(OUT, "index.html");
let html = fs.readFileSync(idx, "utf8");
const metaLive = `<meta name="sfb-live-check" content="${LIVE.replace(/"/g, "")}">`;
const metaBuild = `<meta name="sfb-build" content="${BUILD}">`;
html = html.includes('name="sfb-live-check"') ? html.replace(/<meta name="sfb-live-check"[^>]*>/, metaLive) : html.replace("</head>", `  ${metaLive}\n</head>`);
html = html.includes('name="sfb-build"') ? html.replace(/<meta name="sfb-build"[^>]*>/, metaBuild) : html.replace("</head>", `  ${metaBuild}\n</head>`);
fs.writeFileSync(idx, html);

// sw.js: version + precache list (everything in the shell except the worker itself). The page is cached under
// its root URL "./" only: Cloudflare's auto-trailing-slash handling redirects /index.html to /, and a redirected
// response must never be served for a navigation.
const assets = ["./", ...files.filter((f) => f !== "sw.js" && f !== "index.html" && !f.endsWith(".LICENSE")).map((f) => `./${f}`)];
const swPath = path.join(OUT, "sw.js");
fs.writeFileSync(swPath, fs.readFileSync(swPath, "utf8").replace("__BUILD__", BUILD).replace("__ASSETS__", JSON.stringify(assets)));

// Cloudflare static-asset headers: immutable for versioned packs/fonts/vendor, revalidate the shell.
fs.writeFileSync(path.join(OUT, "_headers"), `/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(self), geolocation=()
/index.html
  Cache-Control: no-cache
/sw.js
  Cache-Control: no-cache
/db/current.json
  Cache-Control: no-cache
/db/*
  Cache-Control: public, max-age=31536000, immutable
/fonts/*
  Cache-Control: public, max-age=31536000, immutable
/vendor/*
  Cache-Control: public, max-age=31536000, immutable
`);

const shellBytes = files.filter((f) => f !== "sw.js").reduce((a, f) => a + fs.statSync(path.join(OUT, f)).size, 0);
const hasDb = fs.existsSync(path.join(OUT, "db", "current.json"));
console.log(`site: ${files.length} shell files, ${(shellBytes / 1024).toFixed(0)} KB (incl. ${(fs.statSync(path.join(OUT, "vendor", "zxing_reader.wasm")).size / 1024).toFixed(0)} KB wasm), build ${BUILD}, live-check ${LIVE || "(off)"}, db ${hasDb ? "present" : "MISSING — run build:db"} -> ${path.relative(APP, OUT)}`);
