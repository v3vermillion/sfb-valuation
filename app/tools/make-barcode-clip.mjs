// make-barcode-clip.mjs — a short Y4M clip of one UPC-A barcode, for Chromium's file-backed fake camera
// (measure.mjs --video). Lets CI measure the real scan path (camera frame -> decoder -> lookup -> sheet) without
// a recorded clip in the repo. Black bars on white, still frames, so two agreeing reads come from consecutive frames.
//   node tools/make-barcode-clip.mjs [--code 078742054261] [--out build/barcode.y4m] [--frames 15]
import fs from "node:fs";
import path from "node:path";
import { checkDigit } from "../public/js/barcode.js";

const args = Object.fromEntries(process.argv.slice(2).map((a, i, arr) => (a.startsWith("--") ? [a.slice(2), arr[i + 1] && !arr[i + 1].startsWith("--") ? arr[i + 1] : true] : [])).filter((x) => x.length));
const OUT = path.resolve(args.out || "build/barcode.y4m");
const FRAMES = Math.max(1, Number(args.frames || 15));
let code = String(args.code || "078742054261").replace(/\D/g, "");
if (code.length === 11) code += String(checkDigit(code));
if (code.length !== 12 || String(checkDigit(code.slice(0, 11))) !== code[11]) {
  console.error(`make-barcode-clip: "${args.code ?? code}" is not a valid UPC-A (11 digits, or 12 with a correct check digit)`);
  process.exit(2);
}

/** UPC-A module pattern: 95 modules, "1" = bar. */
function upcaBits(digits12) {
  const L = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"];
  const R = L.map((p) => p.replace(/[01]/g, (c) => (c === "0" ? "1" : "0")));
  let bits = "101";
  for (let i = 0; i < 6; i++) bits += L[+digits12[i]];
  bits += "01010";
  for (let i = 6; i < 12; i++) bits += R[+digits12[i]];
  return bits + "101";
}

// 640x480 4:2:0, 30 fps. 4 px per module (380 px of bars) centred with a wide quiet zone; bars 220 px tall.
const W = 640, H = 480, MOD = 4, BAR_TOP = 130, BAR_H = 220;
const bits = upcaBits(code);
const left = Math.floor((W - bits.length * MOD) / 2);
const Y = Buffer.alloc(W * H, 235);                 // studio-range white
for (let x = 0; x < bits.length * MOD; x++) {
  if (bits[Math.floor(x / MOD)] !== "1") continue;
  for (let y = BAR_TOP; y < BAR_TOP + BAR_H; y++) Y[y * W + left + x] = 16;   // studio-range black
}
const UV = Buffer.alloc((W / 2) * (H / 2) * 2, 128);  // neutral chroma (U plane then V plane)
const frame = Buffer.concat([Buffer.from("FRAME\n"), Y, UV]);

fs.mkdirSync(path.dirname(OUT), { recursive: true });
const fd = fs.openSync(OUT, "w");
fs.writeSync(fd, `YUV4MPEG2 W${W} H${H} F30:1 Ip A1:1 C420jpeg\n`);
for (let i = 0; i < FRAMES; i++) fs.writeSync(fd, frame);
fs.closeSync(fd);
console.log(`UPC-A ${code}: ${FRAMES} frames ${W}x${H} -> ${OUT} (${(fs.statSync(OUT).size / 1e6).toFixed(1)} MB)`);
