import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { spawn, type ChildProcess } from "node:child_process";

const PORT = 8799;
const BASE = `http://127.0.0.1:${PORT}/mcp`;

let server: ChildProcess;

beforeAll(async () => {
  server = spawn("node", ["dist/index.js"], {
    env: { ...process.env, ALPACA_API_KEY: "test", ALPACA_SECRET_KEY: "test", PORT: String(PORT) },
    stdio: "pipe",
  });
  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("server did not start in time")), 5000);
    server.stdout?.on("data", (chunk) => {
      if (chunk.toString().includes("listening")) {
        clearTimeout(timeout);
        resolve();
      }
    });
    server.on("error", reject);
  });
});

afterAll(() => {
  server.kill();
});

async function initialize(): Promise<string> {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "test", version: "1.0" } },
    }),
  });
  const sessionId = res.headers.get("mcp-session-id");
  if (!sessionId) throw new Error("no session id returned from initialize");

  await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream", "mcp-session-id": sessionId },
    body: JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }),
  });
  return sessionId;
}

function parseSseJson<T>(text: string): T {
  const line = text.split("\n").find((l) => l.startsWith("data: "));
  if (!line) throw new Error(`no data line in SSE response: ${text}`);
  return JSON.parse(line.slice("data: ".length)) as T;
}

describe("sentinel-alpaca-mcp (live server, real MCP protocol)", () => {
  it("completes the initialize handshake and issues a session id", async () => {
    const sessionId = await initialize();
    expect(sessionId).toMatch(/^[0-9a-f-]{36}$/);
  });

  it("lists exactly 6 tools with the correct read-only / destructive annotations", async () => {
    const sessionId = await initialize();
    const res = await fetch(BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream", "mcp-session-id": sessionId },
      body: JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" }),
    });
    const body = parseSseJson<{ result: { tools: Array<{ name: string; annotations?: Record<string, unknown> }> } }>(
      await res.text(),
    );
    const tools = body.result.tools;

    expect(tools.map((t) => t.name).sort()).toEqual([
      "disable_strategy",
      "flatten_position",
      "get_account",
      "get_portfolio_history",
      "get_positions",
      "get_recent_orders",
    ]);

    const readOnlyTools = ["get_account", "get_positions", "get_recent_orders", "get_portfolio_history"];
    const destructiveTools = ["flatten_position", "disable_strategy"];

    for (const name of readOnlyTools) {
      const tool = tools.find((t) => t.name === name)!;
      expect(tool.annotations?.readOnlyHint, `${name} should be readOnlyHint: true`).toBe(true);
      expect(tool.annotations?.destructiveHint, `${name} should be destructiveHint: false`).toBe(false);
    }
    for (const name of destructiveTools) {
      const tool = tools.find((t) => t.name === name)!;
      expect(tool.annotations?.readOnlyHint, `${name} should be readOnlyHint: false`).toBe(false);
      expect(tool.annotations?.destructiveHint, `${name} should be destructiveHint: true`).toBe(true);
    }
  });

  it("fails gracefully (structured error, not a crash) when Alpaca is unreachable", async () => {
    const sessionId = await initialize();
    const res = await fetch(BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json, text/event-stream", "mcp-session-id": sessionId },
      body: JSON.stringify({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "get_account", arguments: {} } }),
    });
    expect(res.status).toBe(200); // MCP reports tool errors in-band, not via HTTP status
    const body = parseSseJson<{ result: { isError?: boolean } }>(await res.text());
    expect(body.result.isError).toBe(true);

    expect(server.exitCode).toBeNull();
  });
});