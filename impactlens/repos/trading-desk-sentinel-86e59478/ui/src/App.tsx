import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { TrueForge, TrueForgeApi, isEventDelta, mergeEventDelta } from "@truefoundry/trueforge-sdk";
import {
  ComposedChart, Area, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  BarChart, Bar, CartesianGrid, Cell, ReferenceLine
} from "recharts";
import InvestigationLoader from "./Preloader";

/* ═══════════════════════════════════════════════════
   VECTOR ICONS (CLEAN SVG)
═══════════════════════════════════════════════════ */
const Icons = {
  Shield: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    </svg>
  ),
  Activity: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  ),
  Play: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <polygon points="5 3 19 12 5 21 5 3"/>
    </svg>
  ),
  Check: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  ),
  AlertTriangle: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
      <line x1="12" y1="9" x2="12" y2="13"/>
      <line x1="12" y1="17" x2="12.01" y2="17"/>
    </svg>
  ),
  Terminal: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="4 17 10 11 4 5"/>
      <line x1="12" y1="19" x2="20" y2="19"/>
    </svg>
  ),
  TrendingUp: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
      <polyline points="17 6 23 6 23 12"/>
    </svg>
  ),
  BarChart2: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="20" x2="18" y2="10"/>
      <line x1="12" y1="20" x2="12" y2="4"/>
      <line x1="6" y1="20" x2="6" y2="14"/>
    </svg>
  ),
  Clock: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
  ),
  Cross: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18"/>
      <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  ),
  Layers: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <polygon points="12 2 2 7 12 12 22 7 12 2"/>
      <polyline points="2 17 12 22 22 17"/>
      <polyline points="2 12 12 17 22 12"/>
    </svg>
  ),
  FileText: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
  ),
  Database: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <ellipse cx="12" cy="5" rx="9" ry="3"/>
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
    </svg>
  ),
  ArrowRight: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="5" y1="12" x2="19" y2="12"/>
      <polyline points="12 5 19 12 12 19"/>
    </svg>
  ),
  ArrowLeft: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="19" y1="12" x2="5" y2="12"/>
      <polyline points="12 19 5 12 12 5"/>
    </svg>
  ),
  Cpu: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
      <rect x="9" y="9" width="6" height="6"/>
      <line x1="9" y1="1" x2="9" y2="4"/>
      <line x1="15" y1="1" x2="15" y2="4"/>
      <line x1="9" y1="20" x2="9" y2="23"/>
      <line x1="15" y1="20" x2="15" y2="23"/>
      <line x1="20" y1="9" x2="23" y2="9"/>
      <line x1="20" y1="14" x2="23" y2="14"/>
      <line x1="1" y1="9" x2="4" y2="9"/>
      <line x1="1" y1="14" x2="4" y2="14"/>
    </svg>
  ),
  Lock: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
    </svg>
  ),
  Search: () => (
    <svg width="1em" height="1em" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="8"/>
      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
  ),
  Loader: () => (
    <svg width="1em" height="1em" className="spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="12" y1="2" x2="12" y2="6"/>
      <line x1="12" y1="18" x2="12" y2="22"/>
      <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"/>
      <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"/>
      <line x1="2" y1="12" x2="6" y2="12"/>
      <line x1="18" y1="12" x2="22" y2="12"/>
      <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"/>
      <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"/>
    </svg>
  )
};

const AGENT_NAME = "trading-desk-sentinel";
const POPULAR_TICKERS = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOGL"];

const defaultAlertFor = (sym: string) =>
  `OAA's paper account equity dropped noticeably in the last session. Investigate and report root cause. Ticker in question: ${sym}`;

type Status = "idle" | "investigating" | "awaiting_approval" | "done" | "error";

type TranscriptItem =
  | { kind: "text"; id: string; text: string }
  | { kind: "tool_call"; id: string; name: string; args: string; destructive: boolean }
  | { kind: "tool_result"; id: string; toolCallId: string; toolName?: string; content: string };

interface PendingApproval {
  toolCallId: string;
  threadId: string;
  toolName: string;
  args: string;
}

interface AccountStats {
  equity: string;
  lastEquity: string;
  currentPrice?: string;
  unrealizedPl?: string;
  unrealizedPlpc?: string;
}

interface PositionItem {
  symbol: string;
  qty: string;
  entryPrice: string;
  currentPrice: string;
  unrealizedPl: string;
  unrealizedPlpc: string;
}

interface OrderItem {
  id: string;
  symbol: string;
  qty: string;
  side: string;
  price: string;
  type: string;
  filledAt: string;
}

const PHASES = [
  { key: "state", name: "1. Account State", hint: "get_account", tools: ["get_account"], desc: "Verifies account equity, status, and buying power baseline." },
  { key: "locate", name: "2. Locate Anomaly", hint: "get_portfolio_history", tools: ["get_portfolio_history"], desc: "Extracts 5-day / 15m historical equity series to isolate drawdown." },
  { key: "fills", name: "3. Responsible Fills", hint: "get_recent_orders", tools: ["get_recent_orders"], desc: "Audits execution order fills and recent trade timings." },
  { key: "exposure", name: "4. Check Exposure", hint: "get_positions", tools: ["get_positions"], desc: "Calculates current asset position sizing and unrealized P&L." },
  { key: "rootcause", name: "5. Root Cause", hint: "AI Reasoning", tools: [], desc: "Synthesizes market conditions, fill prices, and risk factors." },
  { key: "action", name: "6. Propose Action", hint: "flatten / disable", tools: ["flatten_position", "disable_strategy"], desc: "Proposes corrective order execution under human safety gate." },
];

const IRREVERSIBLE_COPY: Record<string, string> = {
  flatten_position: "Closes the open position immediately at market price. This order is non-reversible once submitted to the venue.",
  disable_strategy: "Activates an emergency circuit breaker that halts all automated order routing for this asset.",
};

function currentPhaseIndex(transcript: TranscriptItem[]): number {
  let phase = -1;
  for (const item of transcript) {
    if (item.kind === "tool_call") {
      const idx = PHASES.findIndex((p) => p.tools.includes(item.name));
      if (idx === 5) phase = 5;
      else if (idx !== -1) phase = Math.max(phase, idx);
    } else if (item.kind === "text" && phase === 3) {
      phase = 4;
    }
  }
  return phase;
}

function parseArgs(argsStr: string): [string, string][] | null {
  if (!argsStr.trim()) return [];
  try {
    const obj = JSON.parse(argsStr);
    if (obj && typeof obj === "object" && !Array.isArray(obj)) {
      return Object.entries(obj).map(([k, v]) => [k, typeof v === "string" ? v : JSON.stringify(v)]);
    }
  } catch {
    // Tool arguments may be streamed before they form valid JSON.
  }
  return null;
}

function formatToolOutput(toolName: string | undefined, raw: string): string {
  try {
    const d = JSON.parse(raw);
    if (toolName === "get_portfolio_history") {
      return `Portfolio Baseline: $${(d.base_value || 100000).toLocaleString()}  |  Timeframe: ${d.timeframe || "15Min"}  |  Session Drop: ${d.equity_drop || "-1.02%"}`;
    }
    if (toolName === "get_account") {
      return `Equity: $${parseFloat(d.equity).toLocaleString("en-US", { minimumFractionDigits: 2 })}  |  Last Equity: $${parseFloat(d.last_equity).toLocaleString("en-US", { minimumFractionDigits: 2 })}  |  Buying Power: $${parseFloat(d.buying_power).toLocaleString("en-US", { minimumFractionDigits: 2 })}  |  Status: ${d.status}`;
    }
    if (toolName === "get_positions" && Array.isArray(d)) {
      return d.map(p => `${p.symbol}: ${p.qty} shares  |  Entry: $${p.avg_entry_price || p.current_price}  |  Market: $${p.current_price}  |  P&L: $${parseFloat(p.unrealized_pl).toLocaleString()} (${(parseFloat(p.unrealized_plpc) * 100).toFixed(2)}%)`).join("\n");
    }
    if (toolName === "get_recent_orders" && Array.isArray(d)) {
      return d.map(o => `Order #${o.id}: ${o.side.toUpperCase()} ${o.qty} ${o.symbol} @ $${o.filled_avg_price} (${o.type.toUpperCase()})  ·  Filled: ${o.filled_at}`).join("\n");
    }
    if (toolName === "flatten_position") {
      return `Status: ${d.status.toUpperCase()}  |  Order #${d.order_id}  |  Liquidated ${d.qty} ${d.symbol} @ $${d.filled_avg_price}`;
    }
  } catch {
    // Some diagnostic tools return plain text rather than structured JSON.
  }
  return raw.length > 220 ? raw.slice(0, 220) + "..." : raw;
}

function formatElapsed(ms: number): string {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60).toString().padStart(2, "0");
  const s = (total % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function App() {
  const [baseUrl] = useState(
    () => {
      // Render serves the dashboard and the proxy from the same origin. Keep
      // the browser on that origin so the SDK does not make a cross-origin
      // request that TrueForge may reject due to CORS.
      const configured =
        import.meta.env.VITE_TRUEFORGE_BASE_URL?.trim() ||
        (typeof process !== "undefined" ? process.env.VITE_TRUEFORGE_BASE_URL?.trim() : "");
      const isTest = typeof process !== "undefined" && process.env.NODE_ENV === "test";
      const isRelative = Boolean(configured?.startsWith("/"));
      const allowDirectUrl = import.meta.env.DEV || isTest;
      return configured && (isRelative || allowDirectUrl) ? configured : (isTest
        ? "http://127.0.0.1:8790"
        : "/truforge-api");
    },
  );

  // App Navigation View
  const [currentView, setCurrentView] = useState<"landing" | "analyzer">("landing");


  const [symbol, setSymbol] = useState("AAPL");
  const [alert, setAlert] = useState(defaultAlertFor("AAPL"));
  const [status, setStatus] = useState<Status>("idle");
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [pending, setPending] = useState<PendingApproval[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  // Telemetry data (starts null/empty until investigation is run)
  const [stats, setStats] = useState<AccountStats | null>(null);
  const [historySeries, setHistorySeries] = useState<{ time: string; equity: number }[]>([]);
  const [positions, setPositions] = useState<PositionItem[]>([]);
  const [recentOrders, setRecentOrders] = useState<OrderItem[]>([]);
  const [dashboardReady, setDashboardReady] = useState(true);

  const clientRef = useRef<TrueForge | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const eventsRef = useRef<Map<string, TrueForgeApi.TurnStreamingEvent>>(new Map());
  const startTimeRef = useRef<number | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  const client = useMemo(() => {
    if (!clientRef.current) {
      clientRef.current = new TrueForge({ baseUrl, timeoutInSeconds: 600 });
    }
    return clientRef.current;
  }, [baseUrl]);

  const phase = useMemo(() => currentPhaseIndex(transcript), [transcript]);
  const running = status === "investigating" || status === "awaiting_approval";

  const handleSelectSymbol = (s: string) => {
    const clean = s.toUpperCase().trim();
    setSymbol(clean);
    setAlert(defaultAlertFor(clean));
  };

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      if (startTimeRef.current !== null) setElapsed(Date.now() - startTimeRef.current);
    }, 500);
    return () => window.clearInterval(id);
  }, [running]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [transcript]);

  const appendText = useCallback((id: string, delta: string) => {
    setTranscript((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.kind === "text" && last.id === id) {
        return [...prev.slice(0, -1), { ...last, text: last.text + delta }];
      }
      return [...prev, { kind: "text", id, text: delta }];
    });
  }, []);

  const runTurn = useCallback(
    async (input: TrueForgeApi.TurnInputItem[]) => {
      if (!sessionIdRef.current) return;
      setDashboardReady(false);
      setStatus("investigating");
      setError(null);

      const localPending: TrueForgeApi.ToolApprovalRequiredEvent[] = [];
      const stream = await client.sessions.createTurnStream(sessionIdRef.current, { input });

      for await (const { data: event } of stream.withMetadata()) {
        if (isEventDelta(event)) {
          const existing = eventsRef.current.get(event.id);
          if (existing) mergeEventDelta(existing, event);
          else eventsRef.current.set(event.id, event);
        } else {
          eventsRef.current.set(event.id, event);
        }

        if (event.type === "model.message.delta" && event.threadId === "main") {
          if (event.content) appendText(event.id, event.content);
          if (event.toolCalls?.length) {
            for (const call of event.toolCalls) {
              if (!call.function?.name) continue;
              const destructive = call.function.name === "flatten_position" || call.function.name === "disable_strategy";
              setTranscript((prev) => {
                const rowId = call.id ?? `${event.id}-${call.index}`;
                if (prev.some((r) => r.kind === "tool_call" && r.id === rowId)) return prev;
                return [
                  ...prev,
                  { kind: "tool_call", id: rowId, name: call.function!.name!, args: call.function?.arguments ?? "", destructive },
                ];
              });
            }
          }
        }

        if (event.type === "tool.response") {
          setTranscript((prev) => {
            const call = prev.find((p) => p.kind === "tool_call" && p.id === event.toolCallId);
            const toolName = call?.kind === "tool_call" ? call.name : undefined;

            if (toolName === "get_account") {
              try {
                const d = JSON.parse(event.content);
                setStats((s) => ({ ...(s || { equity: "0", lastEquity: "0" }), equity: d.equity, lastEquity: d.last_equity }));
              } catch {
                // Continue rendering the raw tool output when account data is malformed.
              }
            }
            if (toolName === "get_portfolio_history") {
              try {
                const d = JSON.parse(event.content);
                if (d.equity_series && Array.isArray(d.equity_series)) {
                  setHistorySeries(d.equity_series);
                }
              } catch {
                // Continue rendering the raw tool output when history data is malformed.
              }
            }
            if (toolName === "get_recent_orders") {
              try {
                const d = JSON.parse(event.content);
                if (Array.isArray(d)) {
                  setRecentOrders(d.map((o: Record<string, string>) => ({
                    id: o.id,
                    symbol: o.symbol,
                    qty: o.qty,
                    side: o.side.toUpperCase(),
                    price: o.filled_avg_price,
                    type: o.type.toUpperCase(),
                    filledAt: o.filled_at.split("T")[1]?.slice(0, 8) || o.filled_at,
                  })));
                }
              } catch {
                // Continue rendering the raw tool output when order data is malformed.
              }
            }
            if (toolName === "get_positions") {
              try {
                const d = JSON.parse(event.content);
                if (Array.isArray(d) && d.length) {
                  setStats((s) => ({
                    ...(s || { equity: "0", lastEquity: "0" }),
                    currentPrice: d[0].current_price,
                    unrealizedPl: d[0].unrealized_pl,
                    unrealizedPlpc: d[0].unrealized_plpc,
                  }));
                  setPositions(d.map((p: Record<string, string>) => ({
                    symbol: p.symbol,
                    qty: p.qty,
                    entryPrice: p.avg_entry_price || p.current_price,
                    currentPrice: p.current_price,
                    unrealizedPl: p.unrealized_pl,
                    unrealizedPlpc: p.unrealized_plpc,
                  })));
                }
              } catch {
                // Continue rendering the raw tool output when position data is malformed.
              }
            }

            return [...prev, { kind: "tool_result", id: event.id, toolCallId: event.toolCallId, toolName, content: event.content }];
          });
        }

        if (event.type === "tool.approval_required") localPending.push(event);
      }

      if (localPending.length > 0) {
        const resolved: PendingApproval[] = [];
        for (const p of localPending) {
          for (const ref of p.toolCalls) {
            const source = eventsRef.current.get(ref.sourceEventId);
            if (source?.type !== "model.message.delta") continue;
            const call = source.toolCalls?.find((tc) => tc.id === ref.id);
            if (!call?.function?.name) continue;
            resolved.push({ toolCallId: ref.id, threadId: p.threadId, toolName: call.function.name, args: call.function.arguments ?? "" });
          }
        }
        setPending(resolved);
        setStatus("awaiting_approval");
      } else {
        setStatus("done");
      }
    },
    [client, appendText],
  );

  const startInvestigation = useCallback(async () => {
    setTranscript([]);
    setPending([]);
    setStats(null);
    setHistorySeries([]);
    setPositions([]);
    setRecentOrders([]);
    eventsRef.current = new Map();
    startTimeRef.current = Date.now();
    setElapsed(0);
    try {
      const { data: session } = await client.sessions.create({ agent: { name: AGENT_NAME } });
      sessionIdRef.current = session.id;
      await runTurn([{ type: "user.message", content: alert }]);
    } catch (err) {
      setError(String(err));
      setStatus("error");
    }
  }, [client, alert, runTurn]);

  const respondToApproval = useCallback(
    async (decision: "allow" | "deny") => {
      const approvals: TrueForgeApi.UserToolApprovalEvent[] = pending.map((p) => ({
        type: "user.tool_approval",
        threadId: p.threadId,
        toolCallId: p.toolCallId,
        approval: decision === "allow" ? { status: "allow" } : { status: "deny", reason: "denied via Sentinel UI" },
      }));
      setPending([]);
      try {
        await runTurn(approvals);
      } catch (err) {
        setError(String(err));
        setStatus("error");
      }
    },
    [pending, runTurn],
  );

  const minEquity = historySeries.length ? Math.min(...historySeries.map((d) => d.equity)) : 0;
  const maxEquity = historySeries.length ? Math.max(...historySeries.map((d) => d.equity)) : 100000;
  const isDrawdown = historySeries.length ? historySeries[historySeries.length - 1].equity < historySeries[0].equity : false;
  const tickInterval = Math.max(1, Math.floor(historySeries.length / 6));

  const hasAnalysisData = status !== "idle" && (stats !== null || transcript.length > 0 || historySeries.length > 0);
  const statusLabel: Record<Status, string> = {
    idle: "Standing by",
    investigating: "Investigating",
    awaiting_approval: "Waiting for you",
    done: "Investigation complete",
    error: "Needs attention",
  };
  const activeAction = pending[0];
  const equityChange = stats
    ? parseFloat(stats.equity || "0") - parseFloat(stats.lastEquity || "0")
    : 0;
  const equityChangePercent = stats && parseFloat(stats.lastEquity || "0")
    ? (equityChange / parseFloat(stats.lastEquity)) * 100
    : 0;
  const targetPosition = positions.find((position) => position.symbol === symbol);
  const targetLoss = targetPosition ? parseFloat(targetPosition.unrealizedPl || "0") : 0;
  const actionDisplayName = activeAction?.toolName === "flatten_position"
    ? `Close the ${symbol} position`
    : activeAction?.toolName === "disable_strategy"
      ? `Pause automated ${symbol} trading`
      : "Review the investigation outcome";
  const money = (value: number) => `$${Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const handlePreloaderComplete = useCallback(() => setDashboardReady(true), []);

  return (
    <div className="app">
      {/* ── TOP NAVIGATION (NO ALPACA TAG, FIXED BUTTONS) ── */}
      <header className="topbar">
        <div className="topbar-left">
          <div className="brand" onClick={() => setCurrentView("landing")}>
            <div className="brand-icon">
              <Icons.Shield />
            </div>
            <span className="brand-title">SENTINEL TRADING DESK</span>
            <span className="brand-badge">INCIDENT RESPONSE</span>
          </div>
        </div>

        <div className="topbar-right">
          {currentView === "landing" ? (
            <button
              type="button"
              className="btn-nav-analyze"
              onClick={() => setCurrentView("analyzer")}
            >
              <span>Launch Analyzer</span>
              <Icons.ArrowRight />
            </button>
          ) : (
            <>
              <button
                type="button"
                className="btn-nav-back"
                onClick={() => setCurrentView("landing")}
              >
                <Icons.ArrowLeft />
                <span>Overview</span>
              </button>
              <div className={`status-pill status-${status}`} data-testid="status-pill">
                <span>{statusLabel[status]}</span>
              </div>
              {(running || status === "done" || status === "error") && (
                <div className="time-counter">
                  <Icons.Clock />
                  <span>{formatElapsed(elapsed)}</span>
                </div>
              )}
            </>
          )}
        </div>
      </header>

      {/* ── CONDITIONAL VIEW ROUTING ── */}
      {currentView === "landing" ? (
        /* ═══════════════════════════════════════════════════
           1. ANIMATED LANDING PAGE OVERVIEW
        ═══════════════════════════════════════════════════ */
        <div key="landing" className="landing-container view-frame landing-view">
          <div className="landing-content">
            {/* HERO SECTION */}
            <section className="landing-hero">
              <div className="hero-pill-badge">
                <Icons.Shield />
                <span>Autonomous Incident Surveillance</span>
              </div>

              <h1>
                Autonomous Incident Response for <span>Quantitative Desks</span>
              </h1>

              <p>
                Sentinel continuously audits trading account equity drawdowns, execution anomalies, and open risk exposure.
                Equipped with a 6-step diagnostic playbook and strict <strong>Human-in-the-Loop</strong> safety controls.
              </p>

              <div className="hero-action-buttons">
                <button
                  type="button"
                  className="btn-hero-primary"
                  onClick={() => setCurrentView("analyzer")}
                >
                  <Icons.Play />
                  <span>Launch Incident Analyzer</span>
                </button>
              </div>

              <div className="hero-dashboard-preview" aria-label="Sentinel monitoring preview">
                <div className="preview-orbit preview-orbit-one" />
                <div className="preview-orbit preview-orbit-two" />
                <div className="preview-glow" />
                <div className="preview-main-card">
                  <div className="preview-card-head"><span className="preview-live-dot" /> Live risk surface <span>15M</span></div>
                  <div className="preview-chart">
                    {[34, 48, 42, 64, 57, 80, 69, 94, 76, 88, 102, 92].map((height, index) => (
                      <i key={index} style={{ height: `${height}px`, animationDelay: `${index * 90}ms` }} />
                    ))}
                  </div>
                  <div className="preview-chart-caption"><span>Equity signal</span><strong>MONITORED</strong></div>
                </div>
                <div className="preview-float-card preview-float-left"><span>Exposure</span><strong>Guarded</strong><em>Human approval on</em></div>
                <div className="preview-float-card preview-float-right"><span>Playbook</span><strong>06 steps</strong><em>Forensic response</em></div>
              </div>
            </section>

            {/* KEY FEATURES GRID */}
            <section className="features-grid">
              <div className="feature-card" style={{ animationDelay: "80ms" }}>
                <div className="feature-card-icon">
                  <Icons.Activity />
                </div>
                <h3>Real-Time Telemetry</h3>
                <p>
                  Integrated live with Alpaca Paper Trading Gateway and real-time Yahoo Finance 15-minute intervals for accurate price discovery and portfolio valuation.
                </p>
              </div>

              <div className="feature-card" style={{ animationDelay: "150ms" }}>
                <div className="feature-card-icon">
                  <Icons.Cpu />
                </div>
                <h3>6-Step Forensic Playbook</h3>
                <p>
                  Systematically isolates anomalies by verifying account state, analyzing 5-day historical drawdown curves, auditing order book fills, and checking net exposure.
                </p>
              </div>

              <div className="feature-card" style={{ animationDelay: "220ms" }}>
                <div className="feature-card-icon">
                  <Icons.Lock />
                </div>
                <h3>Human Safety Circuit Breaker</h3>
                <p>
                  Zero unauthorized executions. All irreversible actions—such as market position liquidations or algorithmic kill-switches—require explicit operator sign-off.
                </p>
              </div>
            </section>

            {/* PLAYBOOK WORKFLOW TIMELINE */}
            <section className="playbook-overview-section">
              <div className="section-title-group">
                <h2>6-Step Incident Response Playbook</h2>
                <p>Sentinel systematically executes the following diagnostic protocol to resolve trading desk drawdowns:</p>
              </div>

              <div className="steps-timeline-grid">
                {PHASES.map((p, idx) => (
                  <div key={p.key} className="step-card" style={{ animationDelay: `${idx * 55}ms` }}>
                    <span className="step-number-tag">Phase 0{idx + 1}</span>
                    <h4>{p.name}</h4>
                    <p>{p.desc}</p>
                    <span className="step-tool-badge">Tool: {p.hint}</span>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>
      ) : (
        /* ═══════════════════════════════════════════════════
           2. 3-COLUMN ANALYZER DESK WORKSPACE
        ═══════════════════════════════════════════════════ */
        <div
          key="analyzer"
          className={`workspace view-frame analyzer-view status-${status} ${dashboardReady ? "dashboard-ready" : "dashboard-loading"}`}
          aria-busy={!dashboardReady}
        >
          {/* LEFT COLUMN: CONTROLS & PLAYBOOK */}
          <aside className="col-control">
            <div className="panel-section">
              <label className="panel-header">
                <Icons.Layers />
                <span>Target Asset</span>
              </label>
              <div className="chips-row">
                {POPULAR_TICKERS.map((t) => (
                  <button
                    key={t}
                    type="button"
                    className={`chip-item ${symbol === t ? "active" : ""}`}
                    onClick={() => handleSelectSymbol(t)}
                    disabled={running}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div className="ticker-input-box">
                <span className="ticker-dollar-sign">$</span>
                <input
                  type="text"
                  className="ticker-text-input"
                  value={symbol}
                  onChange={(e) => handleSelectSymbol(e.target.value)}
                  disabled={running}
                  maxLength={5}
                  placeholder="AAPL"
                />
              </div>
            </div>

            <div className="panel-section">
              <label className="panel-header">
                <Icons.FileText />
                <span>Incident Narrative</span>
              </label>
              <textarea
                className="narrative-textarea"
                rows={4}
                value={alert}
                onChange={(e) => setAlert(e.target.value)}
                disabled={running}
              />
            </div>

            <button
              type="button"
              className="btn-dispatch"
              onClick={startInvestigation}
              disabled={running}
            >
              {status === "investigating" ? (
                <>
                  <Icons.Loader />
                  <span>Running Diagnostic Playbook...</span>
                </>
              ) : (
                <>
                  <Icons.Play />
                  <span>Run Investigation</span>
                </>
              )}
            </button>

            {error && <div className="error-box"><Icons.AlertTriangle /> {error}</div>}

            {/* PLAYBOOK RAIL */}
            <div className="playbook-rail-card">
              <div className="playbook-rail-header">
                <label className="panel-header" style={{ margin: 0 }}>
                  <Icons.Activity />
                  <span>Incident Playbook</span>
                </label>
                <span className="playbook-step-badge">
                  {PHASES.filter((_, i) => (status === "done" ? i <= phase : i < phase)).length}/{PHASES.length}
                </span>
              </div>
              <div className="rail-steps-list">
                {PHASES.map((p, i) => (
                  <div
                    key={p.key}
                    className={`rail-step-row ${
                      status === "done" && i <= phase ? "done" : i < phase ? "done" : running && i === phase ? "active" : ""
                    }`}
                  >
                    <div className="rail-step-circle" />
                    <div className="rail-step-meta">
                      <span className="rail-step-title">{p.name}</span>
                      <span className="rail-step-sub">{p.hint}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="control-footer">
              <div className="legend-tag">
                <span className="legend-icon-dot read" />
                <span>Autonomous Read Inspection Tools</span>
              </div>
              <div className="legend-tag">
                <span className="legend-icon-dot write" />
                <span>Approval Gated Destructive Actions</span>
              </div>
            </div>
          </aside>

          {/* CENTER COLUMN: TELEMETRY CHARTS, DIAGNOSTIC LOADER, VERDICT & STREAM */}
          <main className="col-center">
            <div className={`analysis-live-strip ${status === "idle" ? "is-idle" : ""}`}>
              <div className="analysis-live-label">
                <span className="analysis-status-orb" />
                <span>{status === "idle" ? "Investigation control room" : statusLabel[status]}</span>
              </div>
              <div className="analysis-progress-copy">
                {status === "idle"
                  ? "Choose an asset and begin a guided forensic review"
                  : `${Math.max(0, phase + 1)} of ${PHASES.length} playbook stages reached`}
              </div>
              <div className="analysis-stage-dots" aria-label={`${Math.max(0, phase + 1)} of ${PHASES.length} stages reached`}>
                {PHASES.map((item, index) => (
                  <span key={item.key} className={index <= phase ? "is-reached" : index === phase + 1 && running ? "is-next" : ""} />
                ))}
              </div>
            </div>
            {/* 1. IDLE STATE: NOTHING DISPLAYED UNTIL USER CLICKS RUN INVESTIGATION */}
            {status === "idle" && (
              <div className="idle-dispatch-card">
                <div className="idle-icon-wrap">
                  <Icons.Search />
                </div>
                <h3>Sentinel Incident Desk Standing By</h3>
                <p>
                  Select your target asset (<strong>${symbol}</strong>) and narrative in the left panel, then click <strong>Run Investigation</strong> to deploy the autonomous risk audit playbook.
                </p>
              </div>
            )}


            {/* 3. ACTIVE TELEMETRY: DISPLAYED ONLY ONCE RUN/DATA AVAILABLE */}
            {hasAnalysisData && stats && (
              <div className="summary-metrics-bar">
                <div className="summary-card">
                  <div className="summary-card-label">
                    <span>Account Equity</span>
                    <Icons.TrendingUp />
                  </div>
                  <div className="summary-card-value positive">
                    ${parseFloat(stats.equity).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </div>
                  <div className="summary-card-sub">
                    Baseline: ${parseFloat(stats.lastEquity).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </div>
                </div>

                <div className="summary-card">
                  <div className="summary-card-label">
                    <span>{symbol} Market Price</span>
                    <Icons.Activity />
                  </div>
                  <div className="summary-card-value">
                    ${stats.currentPrice ? parseFloat(stats.currentPrice).toFixed(2) : "—"}
                  </div>
                  <div className="summary-card-sub">Yahoo Finance Live Feed</div>
                </div>

                <div className="summary-card">
                  <div className="summary-card-label">
                    <span>Unrealized P&L</span>
                    <Icons.BarChart2 />
                  </div>
                  <div className={`summary-card-value ${parseFloat(stats.unrealizedPl ?? "0") < 0 ? "negative" : "positive"}`}>
                    {stats.unrealizedPl
                      ? `${parseFloat(stats.unrealizedPl) < 0 ? "-" : "+"}$${Math.abs(parseFloat(stats.unrealizedPl)).toLocaleString("en-US", { minimumFractionDigits: 2 })}`
                      : "—"}
                  </div>
                  <div className="summary-card-sub">
                    {stats.unrealizedPlpc ? `${(parseFloat(stats.unrealizedPlpc) * 100).toFixed(2)}% drawdown delta` : "Active Exposure"}
                  </div>
                </div>
              </div>
            )}

            {/* DECISION BRIEF — explains the result in plain language before any action */}
            {hasAnalysisData && (pending.length > 0 || status === "awaiting_approval" || status === "done") && (
              <section className={`final-verdict-card ${status === "done" ? "is-complete" : "is-decision"}`} aria-label="Investigation decision brief">
                <div className="verdict-topline">
                  <span>Decision brief</span>
                  <span className={`verdict-status-tag ${status === "done" ? "tag-resolved" : "tag-pending"}`}>
                    {status === "done" ? "Investigation complete" : "Your decision needed"}
                  </span>
                </div>

                <div className="verdict-summary-row">
                  <div className="verdict-icon-wrap">
                    {status === "done" ? <Icons.Check /> : <Icons.AlertTriangle />}
                  </div>
                  <div className="verdict-summary-text">
                    <h2 className="verdict-summary-title">
                      {status === "done" ? `${symbol} investigation is complete.` : actionDisplayName}
                    </h2>
                    <p className="verdict-summary-sub">
                      {status === "done"
                        ? "The investigation has reached an outcome. The activity trail below records the evidence and the final response."
                        : "Sentinel found enough risk to ask for your approval. Nothing has been changed yet—this is the final safety check."}
                    </p>
                  </div>
                </div>

                <div className="verdict-evidence-grid">
                  <div className="verdict-evidence-item">
                    <span className="evidence-label">Account move</span>
                    <strong className={equityChange < 0 ? "negative" : ""}>
                      {stats ? `${equityChange < 0 ? "−" : "+"}${money(equityChange)}` : "Being assessed"}
                    </strong>
                    <span>{stats ? `${Math.abs(equityChangePercent).toFixed(2)}% from prior close` : "Account baseline unavailable"}</span>
                  </div>
                  <div className="verdict-evidence-item">
                    <span className="evidence-label">{symbol} open P&amp;L</span>
                    <strong className={targetLoss < 0 ? "negative" : ""}>
                      {targetPosition ? `${targetLoss < 0 ? "−" : "+"}${money(targetLoss)}` : "No open position found"}
                    </strong>
                    <span>{targetPosition ? `${targetPosition.qty} shares at $${parseFloat(targetPosition.currentPrice).toFixed(2)}` : "Position check completed"}</span>
                  </div>
                  <div className="verdict-evidence-item">
                    <span className="evidence-label">Confidence</span>
                    <strong>{historySeries.length || positions.length ? "Evidence reviewed" : "In review"}</strong>
                    <span>{historySeries.length ? "Account, price & fills checked" : "Use the diagnostic trail below"}</span>
                  </div>
                </div>

                <div className="verdict-why">
                  <span className="verdict-why-label">Why this matters</span>
                  <p>
                    {targetPosition && targetLoss < 0
                      ? `${symbol} is currently losing ${money(targetLoss)}. Leaving the position open keeps this loss exposed to further price movement.`
                      : stats && equityChange < 0
                        ? `Account equity is down ${money(equityChange)} since the prior close. Sentinel checked recent fills and current exposure to identify the source.`
                        : "Sentinel checked account state, equity history, order fills, and current exposure before reaching this checkpoint."}
                  </p>
                </div>

                {/* Action approval row (only when pending) */}
                {pending.length > 0 && pending.map((p) => {
                  const parsedArgs = parseArgs(p.args);
                  const actionLabel: Record<string, string> = {
                    flatten_position: "Flatten Position — closes trade at market price immediately.",
                    disable_strategy: "Kill Switch — halts all automated order routing for this asset.",
                  };
                  return (
                    <div key={p.toolCallId} className="verdict-action-row">
                      <div className="verdict-action-left">
                        <div className="verdict-action-name">
                          <span className="action-fn-tag">Proposed action</span>
                          <strong>{actionLabel[p.toolName] ?? "Execute corrective desk action."}</strong>
                          {parsedArgs && parsedArgs.length > 0 && (
                            <span className="action-args-inline">
                              {parsedArgs.map(([k, v]) => `${k}: ${v}`).join(" · ")}
                            </span>
                          )}
                        </div>
                        <p className="verdict-action-explain">
                          Approve only if you want Sentinel to carry out this change now. Denying keeps the account unchanged and records your decision.
                          <span className="verdict-irreversible-warn"> {IRREVERSIBLE_COPY[p.toolName] ?? "This action cannot be undone once submitted."}</span>
                        </p>
                      </div>

                      <div className="action-button-group">
                        <button type="button" className="btn-inline-deny" onClick={() => respondToApproval("deny")}>
                          <Icons.Cross />
                          <span>Keep unchanged</span>
                        </button>
                        <button type="button" className="btn-inline-approve" onClick={() => respondToApproval("allow")}>
                          <Icons.Check />
                          <span>Approve action</span>
                        </button>
                      </div>
                    </div>
                  );
                })}

                {/* Done state — no pending action */}
                {status === "done" && pending.length === 0 && (
                  <div className="verdict-resolved-row">
                    <Icons.Check />
                    <span>Incident closed. The corrective action was processed or denied. Review the telemetry stream above for the full diagnostic trail.</span>
                  </div>
                )}
              </section>
            )}

            {/* HISTORICAL DRAWDOWN CHART PANEL (ONLY SHOWN WHEN DATA AVAILABLE) */}
            {hasAnalysisData && historySeries.length > 0 && (
              <div className="chart-panel-card">
                <div className="chart-panel-header">
                  <div className="chart-panel-title">
                    <Icons.TrendingUp />
                    <span>Portfolio Equity Drawdown &amp; Recovery Trajectory</span>
                  </div>
                  <span className="chart-timeframe-badge">5D · 15M INTERVAL</span>
                </div>
                <div className="animated-equity-graph">
                  <span className="graph-scan-beam" aria-hidden="true" />
                  <div className="graph-live-readout">
                    <span className="graph-live-dot" />
                    <span>LIVE EQUITY SIGNAL</span>
                  </div>
                <ResponsiveContainer width="100%" height={170}>
                  <ComposedChart data={historySeries} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="equityRise" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#69e8bd" stopOpacity="0.34" />
                        <stop offset="100%" stopColor="#69e8bd" stopOpacity="0" />
                      </linearGradient>
                      <linearGradient id="equityFall" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ff8fa3" stopOpacity="0.3" />
                        <stop offset="100%" stopColor="#ff8fa3" stopOpacity="0" />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickLine={false} interval={tickInterval} />
                    <YAxis
                      domain={[minEquity * 0.999, maxEquity * 1.001]}
                      stroke="#64748b"
                      fontSize={10}
                      tickLine={false}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0d0f15", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 4, fontSize: 12 }}
                      formatter={(val) => [
                        `$${Number(val ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
                        "Equity",
                      ]}
                    />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke="none"
                      fill={isDrawdown ? "url(#equityFall)" : "url(#equityRise)"}
                      isAnimationActive
                      animationDuration={1500}
                      animationEasing="ease-out"
                    />
                    <Line
                      type="monotone"
                      dataKey="equity"
                      stroke={isDrawdown ? "#f43f5e" : "#10b981"}
                      strokeWidth={2.5}
                      dot={false}
                      activeDot={{ r: 5, strokeWidth: 2, fill: "#101522" }}
                      isAnimationActive
                      animationDuration={1650}
                      animationEasing="ease-out"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* AGENT ACTIVITY FEED */}
            {hasAnalysisData && (
              <>
                <div className="feed-header-title">
                  <Icons.Terminal />
                  <span>Incident Telemetry &amp; Diagnostic Stream</span>
                </div>

                <div className="feed-list">
                  {transcript.map((item) => (
                    <TranscriptRow key={item.id} item={item} />
                  ))}
                  <div ref={transcriptEndRef} />
                </div>
              </>
            )}
          </main>

          {/* RIGHT COLUMN: RISK & POSITION MONITOR */}
          <aside className="col-monitor">
            {/* SAFETY GUARD CARD */}
            <div className="sentinel-guard-card">
              <div className="guard-card-head">
                <Icons.Shield />
                <span className="guard-card-title">Sentinel Protection Active</span>
              </div>
              <p className="guard-card-body">
                Autonomous inspection is active for all read operations. For safety, Sentinel enforces a strict{" "}
                <strong>Human-in-the-Loop approval gate</strong> prior to executing position liquidation or circuit breakers.
              </p>
            </div>

            {/* OPEN POSITIONS TABLE (DISPLAYED ONCE DATA LOADED) */}
            {hasAnalysisData && positions.length > 0 && (
              <div className="monitor-panel-card">
                <div className="monitor-panel-head">
                  <span className="monitor-panel-title">
                    <Icons.Layers />
                    <span>Open Positions</span>
                  </span>
                  <span className="playbook-step-badge">{positions.length} Active</span>
                </div>
                <table className="position-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Qty</th>
                      <th>Price</th>
                      <th>P&amp;L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((p) => (
                      <tr key={p.symbol}>
                        <td style={{ fontWeight: 700 }}>{p.symbol}</td>
                        <td>{p.qty}</td>
                        <td>${parseFloat(p.currentPrice || "0").toFixed(2)}</td>
                        <td className={parseFloat(p.unrealizedPl) < 0 ? "pnl-red" : "pnl-green"}>
                          {parseFloat(p.unrealizedPl) < 0 ? "-" : "+"}${Math.abs(parseFloat(p.unrealizedPl || "0")).toFixed(0)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Mini Exposure Bar Chart */}
                <div className="exposure-chart-box">
                  <ResponsiveContainer width="100%" height={90}>
                    <BarChart data={positions.map(p => ({ symbol: p.symbol, pl: parseFloat(p.unrealizedPl) }))} margin={{ top: 4, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="2 2" stroke="rgba(255,255,255,0.03)" vertical={false} />
                      <XAxis dataKey="symbol" stroke="#64748b" fontSize={10} tickLine={false} />
                      <YAxis stroke="#64748b" fontSize={9} tickLine={false} />
                      <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" />
                      <Bar dataKey="pl" radius={[2, 2, 0, 0]}>
                        {positions.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={parseFloat(entry.unrealizedPl) < 0 ? "#f43f5e" : "#10b981"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* RECENT ORDER BOOK / FILLS (DISPLAYED ONCE DATA LOADED) */}
            {hasAnalysisData && recentOrders.length > 0 && (
              <div className="monitor-panel-card">
                <div className="monitor-panel-head">
                  <span className="monitor-panel-title">
                    <Icons.Database />
                    <span>Execution Order Fills</span>
                  </span>
                  <span className="playbook-step-badge">{recentOrders.length} Logged</span>
                </div>
                <table className="position-table">
                  <thead>
                    <tr>
                      <th>Order</th>
                      <th>Side</th>
                      <th>Price</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentOrders.map((o) => (
                      <tr key={o.id}>
                        <td>#{o.id}</td>
                        <td style={{ color: o.side === "BUY" ? "var(--emerald)" : "var(--rose)", fontWeight: 700 }}>{o.side}</td>
                        <td>${o.price}</td>
                        <td style={{ color: "var(--text-dim)" }}>{o.filledAt}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </aside>
        </div>
      )}

      {/* Stock market investigation loader – overlays workspace while running */}
      <InvestigationLoader
        active={status === "investigating"}
        symbol={symbol}
        onComplete={handlePreloaderComplete}
      />
    </div>
  );
}

/* ─────────────────────────────────────────────
   STREAM ROW COMPONENT
───────────────────────────────────────────── */
function TranscriptRow({ item }: { item: TranscriptItem }) {
  if (item.kind === "text") {
    return <div className="feed-item-card type-text">{item.text}</div>;
  }

  if (item.kind === "tool_call") {
    return (
      <div className={`feed-item-card type-tool ${item.destructive ? "destructive" : ""}`}>
        <div className="tool-badge-row">
          <div className="tool-identity-tag">
            <span className="tool-name-text">{item.name}</span>
          </div>
          <span className="action-status-tag">{item.destructive ? "Action / Gated" : "Inspection / Read-Only"}</span>
        </div>
        {item.args && item.args !== "{}" && (
          <div className="tool-args-snippet">{item.args}</div>
        )}
      </div>
    );
  }

  return (
    <div className="feed-item-card type-result">
      <div className="result-header-tag">
        <Icons.Terminal />
        <span>Output: {item.toolName ?? "Inspection Response"}</span>
      </div>
      <div className="result-summary-box">{formatToolOutput(item.toolName, item.content)}</div>
    </div>
  );
}
