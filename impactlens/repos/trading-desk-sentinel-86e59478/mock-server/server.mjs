import http from "node:http";

const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 8790;
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Remember the target symbol across turns within the same session
const sessionSymbols = new Map();
// Cache market data to avoid re-fetching on the same session
const sessionMarketData = new Map();

/**
 * Fetch real market data from Yahoo Finance for a given symbol.
 * Returns null on failure so callers can fall back to mock data.
 */
async function fetchMarketData(symbol) {
  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=15m&range=5d&includePrePost=false`;
    const res = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; TradingSentinel/1.0)" },
    });
    if (!res.ok) {
      console.warn(`[Yahoo Finance] HTTP ${res.status} for ${symbol}`);
      return null;
    }
    const json = await res.json();
    const result = json?.chart?.result?.[0];
    if (!result) return null;

    const timestamps = result.timestamp;
    const closes = result.indicators.quote[0].close;

    // Filter out any null bars
    const validPoints = timestamps
      .map((t, i) => ({ t, c: closes[i] }))
      .filter((p) => p.c != null);

    if (validPoints.length < 2) return null;

    const currentPrice = validPoints[validPoints.length - 1].c;
    // Use a buy price from ~2 days ago (simulate an open position)
    const buyIndex = Math.max(0, validPoints.length - Math.min(validPoints.length, 26 * 2));
    const buyPrice = validPoints[buyIndex].c;

    const qty = 100;
    const costBasis = buyPrice * qty;
    const currentValue = currentPrice * qty;
    const baseAccountCash = 100000 - costBasis;

    // Build equity curve
    const equitySeries = validPoints.slice(buyIndex).map((p) => ({
      time: new Date(p.t * 1000).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
      equity: parseFloat((baseAccountCash + qty * p.c).toFixed(2)),
    }));

    const unrealizedPl = parseFloat((currentValue - costBasis).toFixed(2));
    const unrealizedPlpc = parseFloat(((currentPrice - buyPrice) / buyPrice).toFixed(4));
    const startEquity = equitySeries[0].equity;
    const endEquity = equitySeries[equitySeries.length - 1].equity;
    const equityDropPct = (((endEquity - startEquity) / startEquity) * 100).toFixed(2);

    console.log(`[Yahoo Finance] ${symbol} currentPrice=$${currentPrice.toFixed(2)} buyPrice=$${buyPrice.toFixed(2)} P&L=$${unrealizedPl}`);

    return {
      symbol,
      qty,
      currentPrice: currentPrice.toFixed(2),
      buyPrice: buyPrice.toFixed(2),
      unrealizedPl: unrealizedPl.toFixed(2),
      unrealizedPlpc: unrealizedPlpc.toFixed(4),
      startEquity: startEquity.toFixed(2),
      endEquity: endEquity.toFixed(2),
      equityDropPct: `${equityDropPct}%`,
      equitySeries,
    };
  } catch (e) {
    console.error(`[Yahoo Finance] Failed to fetch data for ${symbol}:`, e.message);
    return null;
  }
}

const server = http.createServer(async (req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, mcp-session-id");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  let body = "";
  req.on("data", (chunk) => { body += chunk; });

  req.on("end", async () => {
    const url = req.url || "";
    console.log(`[Mock TrueForge] ${req.method} ${url}`);

    if (req.method === "POST" && (url.endsWith("/sessions") || url === "/api/v1/sessions")) {
      const sessionId = `session-${Date.now()}`;
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          data: {
            id: sessionId,
            agent: { type: "reference", name: "trading-desk-sentinel", id: "agent-sentinel" },
            createdAt: new Date().toISOString(),
            status: "idle",
          },
        }),
      );
      return;
    }

    if (req.method === "POST" && (url.includes("/turns") || url.endsWith("/turns"))) {
      res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      });

      const parsed = JSON.parse(body || "{}");
      const inputs = parsed.input || [];
      const isApproval = inputs.some((i) => i.type === "user.tool_approval");

      // Derive session ID from the URL so we can persist the symbol across turns
      const sessionIdMatch = url.match(/sessions\/([^/]+)/);
      const sessionId = sessionIdMatch ? sessionIdMatch[1] : null;

      // On investigation turns, extract the symbol and remember it
      let symbol = "AAPL";
      if (!isApproval) {
        const userMsg = inputs.find((i) => i.type === "user.message")?.content || "";
        const symbolMatch = userMsg.match(/Ticker in question:\s*([A-Z]+)/i);
        symbol = symbolMatch ? symbolMatch[1] : "AAPL";
        if (sessionId) sessionSymbols.set(sessionId, symbol);
      } else {
        // On approval turns there's no user.message — look up from the session map
        symbol = (sessionId && sessionSymbols.get(sessionId)) || "AAPL";
      }

      // Fetch live market data (or reuse cached data for this session)
      let market = sessionId ? sessionMarketData.get(sessionId) : null;
      if (!market && !isApproval) {
        market = await fetchMarketData(symbol);
        if (market && sessionId) sessionMarketData.set(sessionId, market);
      }

      // Fallback mock data if Yahoo Finance is unavailable
      const fallback = {
        symbol,
        qty: 100,
        currentPrice: "215.30",
        buyPrice: "225.50",
        unrealizedPl: "-1020.00",
        unrealizedPlpc: "-0.0452",
        startEquity: "100000.00",
        endEquity: "98980.00",
        equityDropPct: "-1.02%",
        equitySeries: Array.from({ length: 20 }, (_, i) => ({
          time: `T-${20 - i}`,
          equity: 100000 - (i > 14 ? (i - 14) * 204 : 0),
        })),
      };
      const d = market || fallback;

      if (!isApproval) {
        // Step 1: Establish state
        await delay(350);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-1", type: "model.message.delta", thread_id: "main",
            created_at: new Date().toISOString(),
            tool_calls: [{ id: "call-1", index: 0, type: "function", function: { name: "get_account", arguments: "{}" } }],
          })}\n\n`,
        );

        await delay(450);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-2", type: "tool.response", thread_id: "main",
            created_at: new Date().toISOString(), tool_call_id: "call-1",
            content: JSON.stringify({
              equity: d.endEquity,
              last_equity: "100000.00",
              buying_power: (parseFloat(d.endEquity) * 2).toFixed(2),
              status: "ACTIVE",
            }),
          })}\n\n`,
        );

        // Step 2: Locate anomaly
        await delay(450);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-3", type: "model.message.delta", thread_id: "main",
            created_at: new Date().toISOString(),
            tool_calls: [{ id: "call-2", index: 0, type: "function", function: { name: "get_portfolio_history", arguments: '{"period":"1W","timeframe":"15Min"}' } }],
          })}\n\n`,
        );

        await delay(450);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-4", type: "tool.response", thread_id: "main",
            created_at: new Date().toISOString(), tool_call_id: "call-2",
            content: JSON.stringify({
              base_value: 100000,
              timeframe: "15Min",
              equity_drop: d.equityDropPct,
              breakpoint: "2026-08-29T14:15:00Z",
              equity_series: d.equitySeries,
            }),
          })}\n\n`,
        );

        // Step 3: Find responsible fills
        await delay(450);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-5", type: "model.message.delta", thread_id: "main",
            created_at: new Date().toISOString(),
            tool_calls: [{ id: "call-3", index: 0, type: "function", function: { name: "get_recent_orders", arguments: '{"limit":5}' } }],
          })}\n\n`,
        );

        await delay(450);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-6", type: "tool.response", thread_id: "main",
            created_at: new Date().toISOString(), tool_call_id: "call-3",
            content: JSON.stringify([{
              id: "ord-9921", symbol: d.symbol, qty: `${d.qty}`, side: "buy",
              filled_at: "2026-08-29T14:12:30Z",
              filled_avg_price: d.buyPrice, type: "market",
            }]),
          })}\n\n`,
        );

        // Step 4: Check exposure
        await delay(450);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-7", type: "model.message.delta", thread_id: "main",
            created_at: new Date().toISOString(),
            tool_calls: [{ id: "call-4", index: 0, type: "function", function: { name: "get_positions", arguments: "{}" } }],
          })}\n\n`,
        );

        await delay(450);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-8", type: "tool.response", thread_id: "main",
            created_at: new Date().toISOString(), tool_call_id: "call-4",
            content: JSON.stringify([{
              symbol: d.symbol, qty: `${d.qty}`,
              avg_entry_price: d.buyPrice,
              current_price: d.currentPrice,
              unrealized_pl: d.unrealizedPl,
              unrealized_plpc: d.unrealizedPlpc,
            }]),
          })}\n\n`,
        );

        // Step 5: State root cause
        const plSign = parseFloat(d.unrealizedPl) < 0 ? "loss" : "gain";
        const plAbs = Math.abs(parseFloat(d.unrealizedPl)).toLocaleString("en-US", { style: "currency", currency: "USD" });
        const plPct = (Math.abs(parseFloat(d.unrealizedPlpc)) * 100).toFixed(2);
        await delay(600);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-9", type: "model.message.delta", thread_id: "main",
            created_at: new Date().toISOString(),
            content: `Root cause identified: Order #ord-9921 entered ${d.qty} shares of ${d.symbol} at $${d.buyPrice} without an attached stop loss. Current price is $${d.currentPrice}. Position sits at an unrealized ${plSign} of ${plAbs} (${plSign === "loss" ? "-" : "+"}${plPct}%). ${plSign === "loss" ? "Recommending emergency liquidation to prevent further drawdown." : "Position is profitable; monitoring for stop placement."}`,
          })}\n\n`,
        );

        // Step 6: Propose action
        await delay(500);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-10", type: "model.message.delta", thread_id: "main",
            created_at: new Date().toISOString(),
            tool_calls: [{ id: "call-5", index: 0, type: "function", function: { name: "flatten_position", arguments: `{"symbol":"${d.symbol}"}` } }],
          })}\n\n`,
        );

        await delay(200);
        res.write(
          `data: ${JSON.stringify({
            id: "evt-11", type: "tool.approval_required", thread_id: "main",
            created_at: new Date().toISOString(),
            tool_calls: [{ id: "call-5", source_event_id: "evt-10" }],
          })}\n\n`,
        );

        res.end();
      } else {
        const approvalItem = inputs.find((i) => i.type === "user.tool_approval");
        const isAllowed = approvalItem?.approval?.status === "allow";

        await delay(350);
        if (isAllowed) {
          res.write(
            `data: ${JSON.stringify({
              id: "evt-12", type: "tool.response", thread_id: "main",
              created_at: new Date().toISOString(),
              tool_call_id: approvalItem.toolCallId || "call-5",
              content: JSON.stringify({
                status: "filled", order_id: "ord-883921", symbol: d.symbol,
                qty: d.qty, side: "sell", type: "market",
                filled_avg_price: d.currentPrice,
              }),
            })}\n\n`,
          );

          await delay(450);
          res.write(
            `data: ${JSON.stringify({
              id: "evt-13", type: "model.message.delta", thread_id: "main",
              created_at: new Date().toISOString(),
              content: `Position closed at market ($${d.currentPrice}). Risk eliminated and account equity stabilized. Incident response playbook completed.`,
            })}\n\n`,
          );
        } else {
          res.write(
            `data: ${JSON.stringify({
              id: "evt-12", type: "tool.response", thread_id: "main",
              created_at: new Date().toISOString(),
              tool_call_id: approvalItem.toolCallId || "call-5",
              content: JSON.stringify({ status: "denied", reason: approvalItem.approval?.reason || "Denied by supervisor" }),
            })}\n\n`,
          );

          await delay(450);
          res.write(
            `data: ${JSON.stringify({
              id: "evt-13", type: "model.message.delta", thread_id: "main",
              created_at: new Date().toISOString(),
              content: "Liquidation denied by human supervisor. Keeping position open as instructed. No orders submitted.",
            })}\n\n`,
          );
        }
        res.end();
      }
      return;
    }

    res.writeHead(404);
    res.end();
  });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Mock TrueForge server running at http://127.0.0.1:${PORT}`);
});
