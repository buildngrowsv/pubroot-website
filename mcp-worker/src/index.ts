/**
 * Pubroot read-only MCP server — Cloudflare Worker entry point (Workers Free plan).
 *
 * Routes:
 *   POST /mcp      MCP Streamable HTTP (stateless, JSON responses)
 *   GET  /mcp      405 (this server offers no standalone SSE stream; allowed by the spec)
 *   GET  /healthz  {"ok": true, ...}
 *   GET  /         short HTML pointer to https://pubroot.com and /mcp
 *   OPTIONS *      CORS preflight (open CORS for GET/POST/OPTIONS)
 *
 * No Durable Objects, KV, D1, R2, Queues, AI or any other binding is used.
 * Only plain [vars] are read from the environment.
 */

import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";
import type { Env } from "./data.js";
import { countPrepareCalls, rateLimited } from "./ratelimit.js";
import { SERVER_NAME, SERVER_VERSION, createMcpServer } from "./server.js";

// NOTE: the Worker entry module may only export handlers (workerd rejects other
// named exports), so helpers live in their own modules.

/** Max POST body we will read (same 1 MiB cap as the Python HTTP server). */
const MAX_BODY_BYTES = 1024 * 1024;

const CORS_HEADERS: Record<string, string> = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers":
    "content-type, accept, authorization, mcp-session-id, mcp-protocol-version, last-event-id",
  "access-control-expose-headers": "mcp-session-id, mcp-protocol-version",
  "access-control-max-age": "86400",
};

function withCors(resp: Response): Response {
  const headers = new Headers(resp.headers);
  for (const [k, v] of Object.entries(CORS_HEADERS)) headers.set(k, v);
  return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers });
}

function json(data: unknown, status = 200, extra: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...CORS_HEADERS, ...extra },
  });
}

function jsonRpcError(status: number, code: number, message: string, extra: Record<string, string> = {}): Response {
  return json({ jsonrpc: "2.0", error: { code, message }, id: null }, status, extra);
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

async function readBody(request: Request): Promise<string | null> {
  const declared = Number(request.headers.get("content-length") ?? "0");
  if (declared > MAX_BODY_BYTES) return null;
  const buf = await request.arrayBuffer();
  if (buf.byteLength > MAX_BODY_BYTES) return null;
  return new TextDecoder().decode(buf);
}

async function handleMcpPost(request: Request, env: Env): Promise<Response> {
  const text = await readBody(request);
  if (text === null) return jsonRpcError(413, -32600, "Request body too large (max 1 MiB)");

  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    return jsonRpcError(400, -32700, "Parse error: invalid JSON");
  }

  const ip = request.headers.get("cf-connecting-ip") ?? "unknown";
  if (rateLimited(ip, countPrepareCalls(parsed))) {
    return jsonRpcError(429, -32000, "Rate limit exceeded; try again in a minute", { "retry-after": "60" });
  }

  const server = createMcpServer(env);
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined, // stateless
    enableJsonResponse: true,
  });
  await server.connect(transport);
  try {
    const resp = await transport.handleRequest(request, { parsedBody: parsed });
    return withCors(resp);
  } finally {
    await server.close().catch(() => {});
  }
}

const HOME_HTML = `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pubroot MCP</title></head>
<body style="font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5">
<h1>Pubroot MCP server</h1>
<p>Read-only <a href="https://modelcontextprotocol.io">Model Context Protocol</a> endpoint for
<a href="https://pubroot.com">Pubroot</a>, the AI peer-reviewed knowledge base.</p>
<p>MCP endpoint (Streamable HTTP, no auth): <code>POST /mcp</code></p>
<p>Health: <a href="/healthz"><code>/healthz</code></a> &middot; Source:
<a href="https://github.com/buildngrowsv/pubroot-website/tree/main/mcp-worker">mcp-worker/</a></p>
</body></html>
`;

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    if (path === "/mcp") {
      if (request.method === "POST") {
        try {
          return await handleMcpPost(request, env);
        } catch {
          return jsonRpcError(500, -32603, "Internal error");
        }
      }
      // Stateless server: no standalone SSE stream (GET) and no sessions to DELETE.
      return jsonRpcError(405, -32000, "Method not allowed. Use POST /mcp (MCP Streamable HTTP).", {
        allow: "POST, OPTIONS",
      });
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      return json({ error: "Method not allowed" }, 405, { allow: "GET, HEAD, OPTIONS" });
    }

    if (path === "/healthz") {
      return json({ ok: true, service: `${SERVER_NAME}-mcp`, version: SERVER_VERSION });
    }

    if (path === "/") {
      return new Response(HOME_HTML, {
        headers: { "content-type": "text/html; charset=utf-8", ...CORS_HEADERS },
      });
    }

    return json({ error: "Not found", mcp_endpoint: "/mcp", website: "https://pubroot.com" }, 404);
  },
} satisfies ExportedHandler<Env>;
