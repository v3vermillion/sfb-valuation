// serve.mjs — tiny static server that mirrors how Cloudflare serves dist/ (gz packs as opaque bytes,
// correct MIME for wasm/webmanifest, no directory listings).   node tools/serve.mjs dist 8787
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.argv[2] || "dist");
const port = Number(process.argv[3] || 8787);
const MIME = {
  ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8", ".webmanifest": "application/manifest+json", ".wasm": "application/wasm", ".woff2": "font/woff2",
  ".svg": "image/svg+xml", ".png": "image/png", ".gz": "application/octet-stream", ".txt": "text/plain; charset=utf-8", ".LICENSE": "text/plain; charset=utf-8",
};

http.createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  let p = decodeURIComponent(url.pathname);
  // mirror Cloudflare's html_handling = "auto-trailing-slash": /index.html redirects to /
  if (p.endsWith("/index.html")) { res.writeHead(308, { location: p.slice(0, -"index.html".length) + (url.search || "") }); res.end(); return; }
  if (p.endsWith("/")) p += "index.html";
  const file = path.join(root, p);
  if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    // SPA-style fallback only for navigations without an extension
    if (!path.extname(p) && req.headers.accept?.includes("text/html")) { p = "/index.html"; } else { res.writeHead(404); res.end("not found"); return; }
  }
  const f = path.join(root, p);
  const ext = path.extname(f) || path.basename(f).replace(/^[^.]*/, "");
  const noCache = /index\.html$|sw\.js$|current\.json$/.test(f);
  res.writeHead(200, {
    "content-type": MIME[ext] || "application/octet-stream",
    "cache-control": noCache ? "no-cache" : "public, max-age=31536000, immutable",
    "content-length": fs.statSync(f).size,
    "x-content-type-options": "nosniff",
  });
  if (req.method === "HEAD") { res.end(); return; }
  fs.createReadStream(f).pipe(res);
}).listen(port, "127.0.0.1", () => console.log(`serving ${root} on http://127.0.0.1:${port}`));
