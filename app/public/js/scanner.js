// scanner.js — camera barcode scanning with a native-first, wasm-fallback engine.
//
// Engine choice: BarcodeDetector when the browser has it AND it passes a self-test (iOS 18 shipped a
// BarcodeDetector that silently detects nothing), otherwise zxing-cpp (wasm) in a dedicated worker so the
// UI stays at 60fps while frames are decoded. Two agreeing reads are required before a result fires, and a
// code that was just accepted is ignored for a couple of seconds so the item still in frame after
// "Add to tally" does not fire again.

import { toGtin14, checkDigit } from "./barcode.js";

// Retail symbologies only: anything else (Code 128 shipping labels, QR) is not a product code.
const FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e", "itf"];
const ZXING_FORMATS = ["EAN-13", "EAN-8", "UPC-A", "UPC-E", "ITF"];
const DETECT_TIMEOUT_MS = 4000;
const REFIRE_SUPPRESS_MS = 2500;

let enginePromise = null;

/** Draw a UPC-A barcode (for the native self-test). Returns an ImageBitmap. */
async function syntheticUpcA(digits12) {
  const L = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"];
  const R = L.map((p) => p.replace(/[01]/g, (c) => (c === "0" ? "1" : "0")));
  let bits = "101";
  for (let i = 0; i < 6; i++) bits += L[+digits12[i]];
  bits += "01010";
  for (let i = 6; i < 12; i++) bits += R[+digits12[i]];
  bits += "101";
  const mod = 4, quiet = 12 * mod, h = 120;
  const w = bits.length * mod + quiet * 2;
  const c = new OffscreenCanvas(w, h + 40);
  const g = c.getContext("2d");
  g.fillStyle = "#fff"; g.fillRect(0, 0, c.width, c.height);
  g.fillStyle = "#000";
  for (let i = 0; i < bits.length; i++) if (bits[i] === "1") g.fillRect(quiet + i * mod, 20, mod, h);
  return createImageBitmap(c);
}

async function nativeWorks() {
  try {
    if (!("BarcodeDetector" in window)) return false;
    const supported = await window.BarcodeDetector.getSupportedFormats?.();
    if (supported && !supported.includes("upc_a") && !supported.includes("ean_13")) return false;
    const det = new window.BarcodeDetector({ formats: FORMATS.filter((f) => !supported || supported.includes(f)) });
    const body = "07874205426";
    const bmp = await syntheticUpcA(body + checkDigit(body));
    const res = await det.detect(bmp);
    return Array.isArray(res) && res.some((r) => (r.rawValue || "").replace(/\D/g, "").endsWith("78742054261"));
  } catch {
    return false;
  }
}

function makeZxingWorker() {
  // module worker built from a Blob: relative imports are rewritten to absolute URLs so the vendored
  // reader (and its wasm, via locateFile) resolve from any page URL
  const vendor = new URL("../vendor/", new URL("./js/", location.href)).href;
  const code = `
    import { readBarcodes, prepareZXingModule } from ${JSON.stringify(vendor + "zxing-reader.js")};
    prepareZXingModule({ overrides: { locateFile: (f) => ${JSON.stringify(vendor)} + f }, fireImmediately: true });
    self.onmessage = async (e) => {
      const { id, bitmap, width, height } = e.data;
      try {
        const c = new OffscreenCanvas(width, height); const g = c.getContext("2d", { willReadFrequently: true });
        g.drawImage(bitmap, 0, 0, width, height); bitmap.close?.();
        const img = g.getImageData(0, 0, width, height);
        const res = await readBarcodes(img, { formats: ${JSON.stringify(ZXING_FORMATS)}, tryHarder: false, tryRotate: true, tryInvert: false, maxNumberOfSymbols: 1 });
        postMessage({ id, results: res.filter((r) => r.isValid).map((r) => ({ rawValue: r.text, format: r.format, points: r.position ? [r.position.topLeft, r.position.topRight, r.position.bottomRight, r.position.bottomLeft] : null })) });
      } catch (err) { postMessage({ id, error: String(err && err.message || err) }); }
    };`;
  return new Worker(URL.createObjectURL(new Blob([code], { type: "text/javascript" })), { type: "module" });
}

/** Resolve the detection engine once per session (reset on a fatal failure so the next open retries). */
export function getEngine() {
  if (!enginePromise) {
    enginePromise = (async () => {
      if (await nativeWorks()) {
        const det = new window.BarcodeDetector({ formats: FORMATS });
        return { name: "native", detect: async (source) => (await det.detect(source)).map((r) => ({ rawValue: r.rawValue, format: r.format, points: r.cornerPoints })) };
      }
      const w = makeZxingWorker();
      let seq = 0, broken = null; const pending = new Map();
      const failAll = (err) => { broken = err; for (const p of pending.values()) { clearTimeout(p.timer); p.reject(err); } pending.clear(); };
      w.onmessage = (e) => { const p = pending.get(e.data.id); if (!p) return; pending.delete(e.data.id); clearTimeout(p.timer); e.data.error ? p.reject(new Error(e.data.error)) : p.resolve(e.data.results); };
      w.onerror = (e) => failAll(new Error(e.message || "barcode decoder failed to start"));
      return {
        name: "zxing",
        // stop the worker (and the wasm it is fetching or compiling); a later detect fails as "failed to start", so a
        // scanner still holding this engine gives up on it and the next open builds a fresh one
        close: () => { w.terminate(); failAll(new Error("barcode decoder failed to start (closed)")); },
        detect: async (video) => {
          if (broken) throw broken;
          const vw = video.videoWidth, vh = video.videoHeight;
          if (!vw) return [];
          const scale = Math.min(1, 720 / vw);
          const width = Math.round(vw * scale), height = Math.round(vh * scale);
          // no resize options here: Safari ignores/rejects them for video sources; the worker scales when it draws
          const bitmap = await createImageBitmap(video);
          const id = ++seq;
          const pr = new Promise((resolve, reject) => pending.set(id, { resolve, reject, timer: setTimeout(() => { pending.delete(id); reject(new Error("decoder timed out")); }, DETECT_TIMEOUT_MS) }));
          w.postMessage({ id, bitmap, width, height }, [bitmap]);
          const res = await pr;
          // points are in the downscaled frame; map back to video pixels
          return res.map((r) => ({ ...r, points: r.points ? r.points.map((p) => ({ x: p.x / scale, y: p.y / scale })) : null }));
        },
      };
    })();
  }
  return enginePromise;
}

/** Only retail product codes, as the symbology reports them: no digit scraping from other formats. */
function productDigits(r) {
  const v = String(r.rawValue || "");
  if (!/^\d+$/.test(v)) return null;
  const f = String(r.format || "").toLowerCase().replace(/[^a-z0-9]/g, "");
  if (f === "ean13" || f === "upca") return v.length === 12 || v.length === 13 ? v : null;
  if (f === "ean8" || f === "upce") return v.length === 8 ? v : null;
  if (f === "itf") return v.length === 14 ? v : null;
  return [8, 12, 13, 14].includes(v.length) ? v : null;
}

/** Forget an engine nobody will use (the camera was refused) and stop its worker, so the 0.9 MB wasm decoder is not
 *  compiled for nothing while the volunteer types the digits instead. */
function dropEngine(p) {
  if (enginePromise === p) enginePromise = null;
  p.then((engine) => engine.close?.(), () => {});
}

/**
 * Start the camera + detection loop.
 * @param {HTMLVideoElement} video
 * @param {HTMLCanvasElement} overlay
 * @param {(hit:{gtin:object, raw:string, format:string, ms:number}) => void} onHit
 * @param {(info) => void} onStatus   {engine} | {torch} | {error} | {fatal, error}
 */
export async function startScanner(video, overlay, onHit, onStatus) {
  const constraints = { audio: false, video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } } };
  // Ask for the camera first and build the decoder alongside it. A refused or missing camera answers at once (the
  // typed path takes over without waiting for the decoder's self-test or worker), and a granted camera does not wait
  // for the decoder either: the two start together, as before.
  const streamP = navigator.mediaDevices.getUserMedia(constraints);
  const engineP = getEngine();
  engineP.catch(() => {});   // a decoder that fails while the camera is still starting is reported below, not as unhandled
  let stream;
  try { stream = await streamP; } catch (err) { dropEngine(engineP); throw err; }
  let engine;
  try { engine = await engineP; } catch (err) { stream.getTracks().forEach((t) => t.stop()); throw err; }
  onStatus?.({ engine: engine.name });
  video.srcObject = stream;
  await video.play().catch(() => {});
  const track = stream.getVideoTracks()[0];
  const caps = track.getCapabilities?.() || {};
  const hasTorch = !!caps.torch;
  onStatus?.({ engine: engine.name, torch: hasTorch });
  // try to focus continuously; harmless when unsupported
  try { await track.applyConstraints({ advanced: [{ focusMode: "continuous" }] }); } catch { /* optional */ }

  let running = true, stopped = false, busy = false, torchOn = false, errors = 0;
  let lastValue = null, lastCount = 0, lastT = 0;
  let acceptedValue = null, acceptedT = 0;
  const g = overlay.getContext("2d");

  function drawPoints(points) {
    const vw = video.videoWidth, vh = video.videoHeight;
    if (!vw) return;
    const rect = video.getBoundingClientRect();
    overlay.width = rect.width * devicePixelRatio; overlay.height = rect.height * devicePixelRatio;
    g.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    g.clearRect(0, 0, rect.width, rect.height);
    if (!points || points.length < 4) return;
    // object-fit: cover mapping
    const s = Math.max(rect.width / vw, rect.height / vh);
    const ox = (rect.width - vw * s) / 2, oy = (rect.height - vh * s) / 2;
    g.beginPath();
    points.forEach((p, i) => { const x = ox + p.x * s, y = oy + p.y * s; i ? g.lineTo(x, y) : g.moveTo(x, y); });
    g.closePath();
    g.lineWidth = 3; g.strokeStyle = "oklch(85% 0.2 150)"; g.fillStyle = "oklch(85% 0.2 150 / .18)";
    g.fill(); g.stroke();
  }

  async function tick() {
    if (!running || stopped) return;
    if (!busy && video.readyState >= 2) {
      busy = true;
      const t0 = performance.now();
      try {
        const res = await engine.detect(video);
        errors = 0;
        if (!running || stopped) return;                     // stopped or paused while the frame was decoding
        let hit = null, digits = null;
        for (const r of res) { const d = productDigits(r); if (d) { hit = r; digits = d; break; } }
        if (hit) {
          const now = performance.now();
          if (digits === acceptedValue && now - acceptedT < REFIRE_SUPPRESS_MS) { acceptedT = now; lastT = now; drawPoints(hit.points); }   // the item just priced is still in frame
          else {
            if (digits === lastValue && now - lastT < 1500) lastCount++; else { lastValue = digits; lastCount = 1; }
            lastT = now;
            drawPoints(hit.points);
            if (lastCount >= 2) {                              // two agreeing reads, whichever engine
              const gtin = toGtin14(digits, hit.format, { scanned: true });
              acceptedValue = digits; acceptedT = now;
              running = false;
              onHit({ gtin, raw: digits, format: hit.format, points: hit.points, ms: Math.round(now - t0), engine: engine.name });
              return;
            }
          }
        } else if (performance.now() - lastT > 600) {
          drawPoints(null);
        }
      } catch (err) {
        errors++;
        if (errors >= 8 || /failed to start|timed out/.test(String(err?.message))) {
          running = false; enginePromise = null;             // let the next open rebuild the engine
          onStatus?.({ fatal: true, error: String(err?.message || err) });
          return;
        }
        onStatus?.({ error: String(err?.message || err) });
      } finally { busy = false; }
    }
    if (running && !stopped) setTimeout(tick, engine.name === "native" ? 90 : 70);
  }
  tick();

  return {
    engine: engine.name,
    hasTorch,
    async setTorch(on) { try { await track.applyConstraints({ advanced: [{ torch: !!on }] }); torchOn = !!on; return torchOn; } catch { return torchOn; } },
    get torch() { return torchOn; },
    get running() { return running && !stopped; },
    pause() { running = false; drawPoints(null); },
    resume() { if (stopped) return; if (!running) { running = true; lastValue = null; lastCount = 0; drawPoints(null); tick(); } },
    stop() { running = false; stopped = true; stream.getTracks().forEach((t) => t.stop()); video.srcObject = null; drawPoints(null); },
  };
}
