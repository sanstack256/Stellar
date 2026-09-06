const PAPER_BASE_URL = "https://paper-api.alpaca.markets";

export function getAlpacaBaseUrl(): string {
  const envUrl = process.env.ALPACA_BASE_URL;
  if (!envUrl) return PAPER_BASE_URL;

  try {
    const url = new URL(envUrl);
    if (url.origin === PAPER_BASE_URL && url.pathname === "/" && !url.search && !url.hash) {
      return PAPER_BASE_URL;
    }
  } catch {
    // Report malformed URLs using the same safe, user-facing error below.
  }

  throw new Error(
    `Invalid ALPACA_BASE_URL: "${envUrl}". Only the Alpaca paper-trading endpoint is permitted.`,
  );
}

const BASE_URL = getAlpacaBaseUrl();
const API_KEY = process.env.ALPACA_API_KEY ?? "";
const SECRET_KEY = process.env.ALPACA_SECRET_KEY ?? "";

function headers(): Record<string, string> {
  if (!API_KEY || !SECRET_KEY) {
    throw new Error("ALPACA_API_KEY / ALPACA_SECRET_KEY are not set in the MCP server's environment");
  }
  return {
    "APCA-API-KEY-ID": API_KEY,
    "APCA-API-SECRET-KEY": SECRET_KEY,
    "Content-Type": "application/json",
  };
}

async function get(path: string): Promise<unknown> {
  const res = await fetch(`${BASE_URL}${path}`, { headers: headers() });
  if (!res.ok) throw new Error(`Alpaca GET ${path} failed: ${res.status} ${await res.text()}`);
  return res.json();
}

export async function getAccount() {
  return get("/v2/account");
}

export async function getPositions() {
  return get("/v2/positions");
}

export async function getRecentOrders(limit = 20, status: "open" | "closed" | "all" = "all") {
  return get(`/v2/orders?status=${status}&limit=${limit}&direction=desc`);
}

export async function getPortfolioHistory(period = "1M", timeframe = "1D") {
  return get(`/v2/account/portfolio/history?period=${period}&timeframe=${timeframe}`);
}

export async function flattenPosition(symbol: string) {
  const res = await fetch(`${BASE_URL}/v2/positions/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
    headers: headers(),
  });
  if (!res.ok) throw new Error(`Alpaca DELETE position ${symbol} failed: ${res.status} ${await res.text()}`);
  return res.json();
}
