/**
 * Cloudflare Pages Function — proxies /api/* to the Render-hosted FastAPI backend.
 * Set RENDER_API_URL in Cloudflare Pages environment variables if the service name differs.
 */
const DEFAULT_API = "https://northline-returns-api.onrender.com";

export async function onRequest(context) {
  const { request, env, params } = context;
  const base = (env.RENDER_API_URL || DEFAULT_API).replace(/\/$/, "");
  const pathParts = params.path;
  const subpath = Array.isArray(pathParts) ? pathParts.join("/") : pathParts || "";
  const incoming = new URL(request.url);
  const target = `${base}/api/${subpath}${incoming.search}`;

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.set("accept-encoding", "identity");

  const init = {
    method: request.method,
    headers,
    redirect: "follow",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  try {
    const res = await fetch(target, init);
    const outHeaders = new Headers(res.headers);
    outHeaders.set("access-control-allow-origin", "*");
    outHeaders.set(
      "access-control-allow-methods",
      "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    );
    outHeaders.set("access-control-allow-headers", "content-type, authorization");

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: outHeaders });
    }

    return new Response(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: outHeaders,
    });
  } catch (err) {
    return new Response(
      JSON.stringify({
        detail: "Upstream API unreachable. Backend may be cold-starting on Render (wait ~30s and retry).",
        error: String(err),
      }),
      {
        status: 502,
        headers: { "content-type": "application/json", "access-control-allow-origin": "*" },
      }
    );
  }
}
