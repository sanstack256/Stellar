const LOOPBACK_HOSTNAMES = new Set(["127.0.0.1", "localhost", "::1"]);

/**
 * Registering against a deployed (non-loopback) mcp-server without also
 * setting MCP_SHARED_SECRET used to succeed silently: the connector got
 * registered with the loopback default (pointing a deployed TrueForge
 * connector at its own localhost) or, if SENTINEL_MCP_URL was corrected
 * without also setting the secret, an unauthenticated connector that then
 * 401s on every real tool call — Render's generated MCP_SHARED_SECRET
 * protects every deployed request. Fail immediately with the fix instead.
 *
 * Pulled out of register.ts (rather than tested via that file directly)
 * because register.ts calls main() at import time — importing it in a test
 * would perform real registration calls against a TrueForge instance.
 */
export function resolveMcpUrl(env: NodeJS.ProcessEnv = process.env): string {
  const url = env.SENTINEL_MCP_URL ?? "http://127.0.0.1:8791/mcp";
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    throw new Error(`SENTINEL_MCP_URL is not a valid URL: "${url}"`);
  }
  // This connector is an HTTP(S) MCP endpoint — any other scheme (ftp:,
  // ws:, file:, ...) is a misconfiguration that should fail loudly at
  // registration time rather than being silently registered as-is.
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(
      `SENTINEL_MCP_URL must use http or https, got "${parsed.protocol}" in "${url}"`,
    );
  }
  // Node's URL parser keeps the brackets on an IPv6 hostname (e.g. "[::1]"
  // for http://[::1]:8791/mcp), so strip them before comparing against the
  // bare "::1" loopback literal — otherwise IPv6 loopback URLs are (wrongly)
  // treated as deployed and demand a shared secret they don't need.
  const hostname = parsed.hostname.replace(/^\[|\]$/g, "");
  const isLoopback = LOOPBACK_HOSTNAMES.has(hostname);
  if (!isLoopback && !env.MCP_SHARED_SECRET) {
    throw new Error(
      `SENTINEL_MCP_URL ("${url}") is not a loopback address, so this looks like a deployed server ` +
      "(e.g. Render) — those always require MCP_SHARED_SECRET and reject every unauthenticated request " +
      "with 401. Set MCP_SHARED_SECRET to the value Render generated for the sentinel-alpaca-mcp service " +
      "(Render dashboard → sentinel-alpaca-mcp → Environment) before running register. " +
      "See README's \"Deploying to Render\" section for the full command.",
    );
  }
  // register.ts sends MCP_SHARED_SECRET as a bearer token on every request
  // to this URL. Plaintext http: is fine for loopback (traffic never
  // leaves the machine), but for any deployed host it would put the
  // credential — and every authenticated request — on the wire in the
  // clear, interceptable and tamperable in transit. Only loopback gets an
  // http: exemption; every non-loopback host must use https:.
  if (!isLoopback && parsed.protocol !== "https:") {
    throw new Error(
      `SENTINEL_MCP_URL ("${url}") is a non-loopback host using "${parsed.protocol}" — deployed MCP ` +
      "servers must use https: so MCP_SHARED_SECRET isn't sent as a bearer token over plaintext HTTP. " +
      "Use the https:// URL Render gives the sentinel-alpaca-mcp service.",
    );
  }
  return url;
}
