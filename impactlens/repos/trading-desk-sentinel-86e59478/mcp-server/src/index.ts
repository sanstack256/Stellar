import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import {
  getAccount,
  getPositions,
  getRecentOrders,
  getPortfolioHistory,
  flattenPosition,
} from "./alpaca.js";
import { createStrategyStore } from "./strategy-store.js";

const STRATEGY_STATE_PATH = process.env.STRATEGY_STATE_PATH ?? "./strategy_state.json";
const DATABASE_URL = process.env.DATABASE_URL;

// On Render, DATABASE_URL is always set (render.yaml wires it from the
// sentinel-strategy-state database), so disable_strategy persists durably.
// Locally, without a DATABASE_URL, it falls back to STRATEGY_STATE_PATH —
// convenient for `npm run dev`, but never safe to rely on in the deployment,
// since a free Render web service's filesystem is wiped on every restart,
// redeploy, or spin-down.
if (!DATABASE_URL) {
  console.warn(
    `DATABASE_URL not set; disable_strategy will persist to ${STRATEGY_STATE_PATH}. ` +
      "That's fine for local development, but this must never be the case when " +
      "running on Render's free plan — its filesystem is ephemeral.",
  );
}
const strategyStore = createStrategyStore(DATABASE_URL, STRATEGY_STATE_PATH);

function buildServer(): McpServer {
  const server = new McpServer({ name: "sentinel-alpaca-mcp", version: "0.1.0" });


  server.registerTool(
    "get_account",
    {
      title: "Get Account",
      description:
        "OAA's paper-trading account summary: equity, buying power, last_equity, daily P&L basis. Read-only.",
      inputSchema: {},
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    },
    async () => {
      const account = await getAccount();
      return { content: [{ type: "text", text: JSON.stringify(account, null, 2) }] };
    },
  );

  server.registerTool(
    "get_positions",
    {
      title: "Get Open Positions",
      description: "All open positions in OAA's paper account: symbol, qty, avg entry, unrealized P&L. Read-only.",
      inputSchema: {},
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    },
    async () => {
      const positions = await getPositions();
      return { content: [{ type: "text", text: JSON.stringify(positions, null, 2) }] };
    },
  );

  server.registerTool(
    "get_recent_orders",
    {
      title: "Get Recent Orders",
      description:
        "Recent orders (default last 20, all statuses) — use this to find the fill(s) that preceded an anomaly. Read-only.",
      inputSchema: {
        limit: z.number().int().min(1).max(200).default(20).describe("Max orders to return"),
        status: z.enum(["open", "closed", "all"]).default("all"),
      },
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    },
    async ({ limit, status }) => {
      const orders = await getRecentOrders(limit, status);
      return { content: [{ type: "text", text: JSON.stringify(orders, null, 2) }] };
    },
  );

  server.registerTool(
    "get_portfolio_history",
    {
      title: "Get Portfolio History",
      description:
        "Equity curve over a period (default 1 month, daily) — use this to locate exactly when a drawdown started. Read-only.",
      inputSchema: {
        period: z.string().default("1M").describe("e.g. 1D, 1W, 1M, 3M, 1A"),
        timeframe: z.string().default("1D").describe("e.g. 1Min, 5Min, 15Min, 1D"),
      },
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true },
    },
    async ({ period, timeframe }) => {
      const history = await getPortfolioHistory(period, timeframe);
      return { content: [{ type: "text", text: JSON.stringify(history, null, 2) }] };
    },
  );


  server.registerTool(
    "flatten_position",
    {
      title: "Flatten Position (IRREVERSIBLE)",
      description:
        "Closes one open position at market. Irreversible once filled — this is exactly the kind of action " +
        "that must never run without a human's explicit sign-off. Only call this after the investigation is " +
        "complete and root cause is stated; TrueForge will pause and ask a human to approve or deny regardless.",
      inputSchema: { symbol: z.string().describe("Ticker of the position to close, e.g. SPY") },
      annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: false, openWorldHint: true },
    },
    async ({ symbol }) => {
      const result = await flattenPosition(symbol);
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    },
  );

  server.registerTool(
    "disable_strategy",
    {
      title: "Disable Strategy (IRREVERSIBLE until re-enabled)",
      description:
        "Records a kill-switch entry that a patched OAA main.py polls via this server's " +
        "GET /strategy-state endpoint before scanning a symbol — the documented integration point " +
        "between this incident responder and the OAA pipeline built separately. Polling this endpoint, " +
        "rather than reading a local file, means the disable is observed by OAA the same way whether " +
        "this server is backed by Postgres (Render) or the local file fallback (npm run dev). Disabling " +
        "stops OAA from opening any NEW position; it does not touch existing ones (use flatten_position " +
        "for that). Only call after root cause is established.",
      inputSchema: {
        symbol: z.string().describe("Watchlist symbol to disable, e.g. SPY"),
        reason: z.string().describe("Root-cause summary to record alongside the kill-switch"),
      },
      annotations: { readOnlyHint: false, destructiveHint: true, idempotentHint: true, openWorldHint: false },
    },
    async ({ symbol, reason }) => {
      const { at } = await strategyStore.disable(symbol, reason);
      return {
        content: [
          { type: "text", text: `Disabled ${symbol} at ${at}. Recorded in ${strategyStore.description}: ${reason}` },
        ],
      };
    },
  );

  return server;
}

const app = express();
app.use(express.json());

app.get("/health", async (_req, res) => {
  try {
    await strategyStore.checkHealth();
    res.status(200).json({ status: "ok" });
  } catch (err) {
    // Render polls this to decide whether to route traffic and whether to
    // restart the service. Reporting "ok" while the kill-switch store is
    // unreachable would hide an outage that makes disable_strategy silently
    // fail — surface it as unhealthy instead.
    console.error("Health check failed: strategy store unreachable:", err);
    res.status(503).json({ status: "error", detail: "strategy store unreachable" });
  }
});

const SHARED_SECRET = process.env.MCP_SHARED_SECRET;
if (SHARED_SECRET) {
  const requireSharedSecret: express.RequestHandler = (req, res, next) => {
    const provided = req.headers["authorization"];
    if (provided === `Bearer ${SHARED_SECRET}`) {
      next();
      return;
    }
    res.status(401).json({ error: "Missing or invalid Authorization header." });
  };
  app.use("/mcp", requireSharedSecret);
  // OAA polls this with the same shared secret; it carries the same
  // kill-switch reasons the MCP tool records, so it gets the same gate.
  app.use("/strategy-state", requireSharedSecret);
}

// Read-only integration point for the separately-built OAA pipeline: the
// documented contract is "poll this endpoint before scanning a symbol,"
// not "read a local file." That keeps OAA's view of the kill-switch
// correct regardless of whether disable_strategy is currently backed by
// Postgres (Render) or the local strategy_state.json fallback (dev).
app.get("/strategy-state", async (_req, res) => {
  try {
    const state = await strategyStore.getState();
    res.status(200).json(state);
  } catch (err) {
    console.error("Failed to read strategy state:", err);
    res.status(502).json({ error: "Failed to read strategy state." });
  }
});

const transports = new Map<string, StreamableHTTPServerTransport>();

app.all("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"] as string | undefined;

  let transport = sessionId ? transports.get(sessionId) : undefined;

  if (!transport && !sessionId && isInitializeRequest(req.body)) {
    transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => randomUUID(),

      onsessioninitialized: (id) => { transports.set(id, transport!); },
    });
    transport.onclose = () => {
      if (transport!.sessionId) transports.delete(transport!.sessionId);
    };
    const server = buildServer();
    await server.connect(transport);
  }

  if (!transport) {
    res.status(400).json({ error: "No valid session; send an initialize request first." });
    return;
  }

  await transport.handleRequest(req, res, req.body);
});

const PORT = Number(process.env.PORT ?? 8791);
// Bound to loopback by default, matching the README's documented
// `http://127.0.0.1:8791/mcp` quick-start URL. This matters because
// MCP_SHARED_SECRET is normally unset in local dev (see the Quick start
// section) — binding 0.0.0.0 by default would put an unauthenticated MCP
// server, including the /strategy-state kill-switch reader, on the LAN.
// The Render deployment overrides this via the HOST env var in render.yaml.
const HOST = process.env.HOST ?? "127.0.0.1";
app.listen(PORT, HOST, () => {
  console.log(`sentinel-alpaca-mcp listening on http://${HOST}:${PORT}/mcp`);
});
