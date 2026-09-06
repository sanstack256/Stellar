import { describe, it, expect } from "vitest";
import { resolveMcpUrl } from "./resolve-mcp-url.js";

describe("resolveMcpUrl", () => {
  it("defaults to the loopback address, no secret required", () => {
    expect(resolveMcpUrl({})).toBe("http://127.0.0.1:8791/mcp");
  });

  it("allows an explicit loopback URL without a secret (local dev)", () => {
    expect(resolveMcpUrl({ SENTINEL_MCP_URL: "http://localhost:8791/mcp" })).toBe("http://localhost:8791/mcp");
  });

  // Regression coverage for the Qodo finding "Deployment registration
  // remains local": a deployed URL without the matching secret must fail
  // loudly at registration time, not register an unauthenticated connector
  // that 401s on every real tool call.
  it("throws when a non-loopback URL is given without MCP_SHARED_SECRET", () => {
    expect(() => resolveMcpUrl({ SENTINEL_MCP_URL: "https://sentinel-alpaca-mcp.onrender.com/mcp" })).toThrow(
      /MCP_SHARED_SECRET/,
    );
  });

  it("accepts a non-loopback URL once MCP_SHARED_SECRET is set", () => {
    const url = resolveMcpUrl({
      SENTINEL_MCP_URL: "https://sentinel-alpaca-mcp.onrender.com/mcp",
      MCP_SHARED_SECRET: "generated-secret",
    });
    expect(url).toBe("https://sentinel-alpaca-mcp.onrender.com/mcp");
  });

  it("throws a clear error for a malformed URL", () => {
    expect(() => resolveMcpUrl({ SENTINEL_MCP_URL: "not a url" })).toThrow(/not a valid URL/);
  });

  // Regression coverage for the Qodo finding "Unsupported mcp schemes
  // accepted": a syntactically valid but non-HTTP(S) URL (e.g. ftp:) must
  // be rejected rather than registered as a usable MCP endpoint.
  it("rejects a non-http(s) scheme even when the host is loopback", () => {
    expect(() => resolveMcpUrl({ SENTINEL_MCP_URL: "ftp://127.0.0.1:8791/mcp" })).toThrow(
      /must use http or https/,
    );
  });

  // Regression coverage for the Qodo finding "Ipv6 loopback rejected":
  // new URL(...).hostname keeps the brackets on an IPv6 literal ("[::1]"),
  // so this must be recognized as loopback rather than treated as deployed.
  it("recognizes the IPv6 loopback address, no secret required", () => {
    expect(resolveMcpUrl({ SENTINEL_MCP_URL: "http://[::1]:8791/mcp" })).toBe("http://[::1]:8791/mcp");
  });

  // Regression coverage for the Qodo finding "Bearer secret sent
  // plaintext": a non-loopback URL must use https: even when
  // MCP_SHARED_SECRET is set, since register.ts sends that secret as a
  // bearer token on every request to this URL.
  it("rejects a plaintext http:// URL for a non-loopback host, even with the secret set", () => {
    expect(() =>
      resolveMcpUrl({
        SENTINEL_MCP_URL: "http://sentinel-alpaca-mcp.onrender.com/mcp",
        MCP_SHARED_SECRET: "generated-secret",
      }),
    ).toThrow(/must use https/);
  });
});
