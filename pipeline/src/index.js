// sfb-pipeline — signs Walmart I/O Affiliate API requests.
// Secrets (Cloudflare): WM_PRIVATE_KEY, WM_CONSUMER_ID, ADMIN_TOKEN. Var: WM_KEY_VERSION.

const API = "https://developer.api.walmart.com/api-proxy/service/affil/product/v2";

function pemToDer(pem) {
  const b64 = pem
    .replace(/\\n/g, "\n")
    .replace(/-----BEGIN [^-]+-----/, "")
    .replace(/-----END [^-]+-----/, "")
    .replace(/\s+/g, "");
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out.buffer;
}

let cachedKey = null;
async function privateKey(env) {
  if (!cachedKey) {
    cachedKey = await crypto.subtle.importKey(
      "pkcs8", pemToDer(env.WM_PRIVATE_KEY),
      { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
  }
  return cachedKey;
}

async function walmartHeaders(env) {
  const ts = Date.now().toString();
  const ver = env.WM_KEY_VERSION || "1";
  const toSign = `${env.WM_CONSUMER_ID}\n${ts}\n${ver}\n`;
  const sig = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", await privateKey(env), new TextEncoder().encode(toSign));
  return {
    "WM_CONSUMER.ID": env.WM_CONSUMER_ID,
    "WM_CONSUMER.INTIMESTAMP": ts,
    "WM_SEC.KEY_VERSION": ver,
    "WM_SEC.AUTH_SIGNATURE": btoa(String.fromCharCode(...new Uint8Array(sig))),
    "Accept": "application/json",
  };
}

export async function walmartGet(env, path) {
  const res = await fetch(`${API}${path}`, { headers: await walmartHeaders(env) });
  const body = await res.text();
  return { status: res.status, body };
}

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj, null, 2), { status, headers: { "content-type": "application/json" } });

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!env.ADMIN_TOKEN || url.searchParams.get("token") !== env.ADMIN_TOKEN) {
      return json({ error: "unauthorized" }, 401);
    }

    if (url.pathname === "/health") {
      return json({
        WM_PRIVATE_KEY: Boolean(env.WM_PRIVATE_KEY),
        WM_CONSUMER_ID: Boolean(env.WM_CONSUMER_ID),
        WM_KEY_VERSION: env.WM_KEY_VERSION || null,
      });
    }

    if (url.pathname === "/taxonomy") {
      try {
        const { status, body } = await walmartGet(env, "/taxonomy");
        let parsed;
        try { parsed = JSON.parse(body); } catch { parsed = body.slice(0, 2000); }
        if (status !== 200) return json({ walmart_status: status, response: parsed }, 502);
        const top = (parsed.categories || []).map(c => ({ id: c.id, name: c.name, children: (c.children || []).length }));
        return json({ walmart_status: status, top_level_count: top.length, top_level: top });
      } catch (e) {
        return json({ error: String(e) }, 500);
      }
    }

    return json({ error: "not found", routes: ["/health", "/taxonomy"] }, 404);
  },
};
