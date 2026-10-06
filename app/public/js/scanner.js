// scanner.js — camera barcode scanning with a native-first, wasm-fallback engine.
//
// Engine choice: BarcodeDetector when the browser has it AND it passes a self-test (iOS 18 shipped a
// BarcodeDetector that silently detects nothing), otherwise zxing-wasm running in a dedicated worker so
// the UI stays at 60fps while frames are decoded. Detection requires two agreeing reads (or one native
// read) before it fires, which removes the misreads that make volunteers distrust a scanner.

import { toGtin14, checkDigit } from "./barcode.js";

const FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e", "itf", "code_128"];
const ZXING_FORMATS = ["EAN-13", "EAN-8", "UPC-A", "UPC-E", "ITF", "Code128"];

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
  // module worker: imports the vendored zxing-wasm reader; wasm is fetched relative to the module
  const code = `
    import { readBarcodes, prepareZXingModule } from "../vendor/zxing-reader.js";
    prepareZXingModule({ overrides: { locateFile: (f) => new URL("../vendor/" + f, import.meta.url).href }, fireImmediately: true });
    self.onmessage = async (e) => {
      const { id, bitmap, width, height } = e.data;
      try {
        const c = new OffscreenCanvas(width, height); const g = c.getContext("2d", { willReadFrequently: true });
        g.drawImage(bitmap, 0, 0, width, height); bitmap.close?.();
        const img = g.getImageData(0, 0, width, height);
        const res = await readBarcodes(img, { formats: ${JSON.stringify(ZXING_FORMATS)}, tryHarder: false, tryRotate: true, tryInvert: false, maxNumberOfSymbols: 1 });
        postMessage({ id, results: res.filter((r) => r.isValid).map((r) => ({ rawValue: r.text, format: r.format, points: r.position ? [r.position.topLeft, r.position.topRight, r.position.bottomRight, r.position.bottomLeft] : null })) });
      } catch (err) { postMessage({ id, error: String(err) }); }
    };`;
  const blob = new Blob([code], { type: "text/javascript" });
  // Blob workers lose the base URL; build with an absolute import by rewriting relative paths
  const base = new URL("./js/", location.href).href;
  const abs = code.replaceAll('"../vendor/zxing-reader.js"', JSON.stringify(new URL("../vendor/zxing-reader.js", base).href)).replace('new URL("../vendor/" + f, import.meta.url).href', `${JSON.stringify(new URL("../vendor/", base).href)} + f`);
  URL.revokeObjectURL; // no-op reference keeps linters quiet
  return new Worker(URL.createObjectURL(new Blob([abs], { type: "text/javascript" })), { type: "module" });
}

/** Resolve the detection engine once per session. */
export function getEngine() {
  if (!enginePromise) {
    enginePromise = (async () => {
      if (await nativeWorks()) {
        const det = new window.BarcodeDetector({ formats: FORMATS });
        return { name: "native", detect: async (source) => (await det.detect(source)).map((r) => ({ rawValue: r.rawValue, format: r.format, points: r.cornerPoints })) };
      }
      const w = makeZxingWorker();
      let seq = 0; const pending = new Map();
      w.onmessage = (e) => { const p = pending.get(e.data.id); if (!p) return; pending.delete(e.data.id); e.data.error ? p.reject(new Error(e.data.error)) : p.resolve(e.data.results); };
      return {
        name: "zxing",
        detect: async (video) => {
          const vw = video.videoWidth, vh = video.videoHeight;
          if (!vw) return [];
          const scale = Math.min(1, 720 / vw);
          const width = Math.round(vw * scale), height = Math.round(vh * scale);
          // no resize options here: Safari ignores/rejects them for video sources; the worker scales when it draws
          const bitmap = await createImageBitmap(video);
          const id = ++seq;
          const pr = new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
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

/**
 * Start the camera + detection loop.
 * @param {HTMLVideoElement} video
 * @param {HTMLCanvasElement} overlay
 * @param {(hit:{gtin:object, raw:string, format:string, ms:number}) => void} onHit
 * @param {(info) => void} onStatus
 */
export async function startScanner(video, overlay, onHit, onStatus) {
  const engine = await getEngine();
  onStatus?.({ engine: engine.name });
  const constraints = { audio: false, video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 }, frameRate: { ideal: 30 } } };
  const stream = await navigator.mediaDevices.getUserMedia(constraints);
  video.srcObject = stream;
  await video.play().catch(() => {});
  const track = stream.getVideoTracks()[0];
  const caps = track.getCapabilities?.() || {};
  const hasTorch = !!caps.torch;
  onStatus?.({ engine: engine.name, torch: hasTorch });
  // try to focus continuously; harmless when unsupported
  try { await track.applyConstraints({ advanced: [{ focusMode: "continuous" }] }); } catch { /* optional */ }

  let running = true, busy = false, torchOn = false;
  let lastValue = null, lastCount = 0, lastT = 0;
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
    if (!running) return;
    if (!busy && video.readyState >= 2) {
      busy = true;
      const t0 = performance.now();
      try {
        const res = await engine.detect(video);
        const hit = res.find((r) => /^\d{8,14}$/.test((r.rawValue || "").replace(/\D/g, "")));
        if (hit) {
          const digits = hit.rawValue.replace(/\D/g, "");
          const now = performance.now();
          if (digits === lastValue && now - lastT < 1500) lastCount++; else { lastValue = digits; lastCount = 1; }
          lastT = now;
          drawPoints(hit.points);
          const needed = engine.name === "native" ? 1 : 2;
          if (lastCount >= needed) {
            const gtin = toGtin14(digits, hit.format);
            running = false;
            onHit({ gtin, raw: digits, format: hit.format, points: hit.points, ms: Math.round(now - t0), engine: engine.name });
            return;
          }
        } else if (performance.now() - lastT > 600) {
          drawPoints(null);
        }
      } catch (err) {
        onStatus?.({ error: String(err) });
      } finally { busy = false; }
    }
    if (running) setTimeout(tick, engine.name === "native" ? 90 : 70);
  }
  tick();

  return {
    engine: engine.name,
    hasTorch,
    async setTorch(on) { try { await track.applyConstraints({ advanced: [{ torch: !!on }] }); torchOn = !!on; return torchOn; } catch { return torchOn; } },
    get torch() { return torchOn; },
    resume() { if (!running) { running = true; lastValue = null; lastCount = 0; drawPoints(null); tick(); } },
    stop() { running = false; stream.getTracks().forEach((t) => t.stop()); video.srcObject = null; drawPoints(null); },
  };
}
