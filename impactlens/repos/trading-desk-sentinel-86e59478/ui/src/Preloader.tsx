import React, { useEffect, useRef, useState } from "react";
import "./preloader.css";

const TICKER_STREAM = [
  { sym: "AAPL",  price: "213.49", change: "+1.23", up: true  },
  { sym: "TSLA",  price: "248.91", change: "-3.14", up: false },
  { sym: "NVDA",  price: "138.22", change: "+4.78", up: true  },
  { sym: "MSFT",  price: "416.37", change: "+0.94", up: true  },
  { sym: "AMZN",  price: "199.02", change: "+2.11", up: true  },
  { sym: "GOOGL", price: "178.65", change: "-1.08", up: false },
  { sym: "META",  price: "589.44", change: "+7.32", up: true  },
  { sym: "SPY",   price: "563.18", change: "-0.42", up: false },
  { sym: "QQQ",   price: "487.21", change: "+1.67", up: true  },
  { sym: "BRK.B", price: "450.99", change: "+0.33", up: true  },
];

// Candlestick chart OHLC bars
const CANDLE_DATA = [
  { o: 58, h: 75, l: 52, c: 68, up: true  },
  { o: 68, h: 80, l: 60, c: 62, up: false },
  { o: 62, h: 70, l: 50, c: 64, up: true  },
  { o: 64, h: 85, l: 61, c: 82, up: true  },
  { o: 82, h: 90, l: 75, c: 77, up: false },
  { o: 77, h: 88, l: 72, c: 86, up: true  },
  { o: 86, h: 96, l: 82, c: 90, up: true  },
  { o: 90, h: 92, l: 70, c: 72, up: false },
  { o: 72, h: 80, l: 68, c: 78, up: true  },
  { o: 78, h: 88, l: 74, c: 85, up: true  },
  { o: 85, h: 93, l: 80, c: 88, up: true  },
  { o: 88, h: 91, l: 68, c: 70, up: false },
];

const SCAN_STEPS = [
  "Connecting to live market gateway...",
  "Streaming order book L2 feed...",
  "Loading historical 5D OHLCV data...",
  "Calibrating risk models and VaR...",
  "Initializing autonomous playbook engine...",
  "Dispatching diagnostic agent...",
];

interface InvestigationLoaderProps {
  /** Whether the investigation is actively running */
  active: boolean;
  symbol: string;
  /** Called after the exit animation has fully completed. */
  onComplete?: () => void;
}

export default function InvestigationLoader({ active, symbol, onComplete }: InvestigationLoaderProps) {
  const [visible, setVisible] = useState(false);
  const [fadeOut, setFadeOut] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const wasActive = useRef(false);

  // Show when active becomes true
  useEffect(() => {
    if (active) {
      wasActive.current = true;
      setVisible(true);
      setFadeOut(false);
      setScanStep(0);
    } else if (visible && wasActive.current) {
      // Trigger fade-out then unmount
      setFadeOut(true);
      const t = setTimeout(() => {
        setVisible(false);
        wasActive.current = false;
        onComplete?.();
      }, 550);
      return () => clearTimeout(t);
    }
  }, [active, visible, onComplete]);

  // Cycle through scan steps while visible & active
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => {
      setScanStep((prev) => (prev < SCAN_STEPS.length - 1 ? prev + 1 : prev));
    }, 480);
    return () => clearInterval(id);
  }, [active]);

  if (!visible) return null;

  return (
    <div className={`investigation-loader-overlay ${fadeOut ? "loader-fadeout" : "loader-fadein"}`}>

      {/* ── TOP SCROLLING TICKER TAPE ── */}
      <div className="ticker-tape">
        <div className="ticker-track">
          {[...TICKER_STREAM, ...TICKER_STREAM].map((t, i) => (
            <span key={i} className={`ticker-item ${t.up ? "tick-up" : "tick-down"}`}>
              <span className="tick-sym">{t.sym}</span>
              <span className="tick-price">{t.price}</span>
              <span className="tick-change">{t.change}</span>
              <span className="tick-sep">·</span>
            </span>
          ))}
        </div>
      </div>

      {/* ── MAIN BODY ── */}
      <div className="loader-body">

        {/* Header */}
        <div className="loader-brand-row">
          <div className="loader-shield">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div>
            <div className="loader-brand-title">SENTINEL INCIDENT ANALYZER</div>
            <div className="loader-brand-sub">Forensic Diagnostic Playbook Running</div>
          </div>
          <div className="loader-ticker-badge">${symbol}</div>
        </div>

        {/* Candlestick chart visualization */}
        <div className="loader-candle-chart">
          <div className="loader-chart-header">
            <span className="loader-chart-label">
              <span className="live-dot" />
              {symbol} · 15M · LIVE FEED
            </span>
            <span className="loader-chart-tag">FORENSIC SCAN</span>
          </div>

          <svg className="candle-chart-svg" viewBox="0 0 520 130" preserveAspectRatio="xMidYMid meet">
            {/* Grid */}
            {[25, 55, 85, 115].map((y) => (
              <line key={y} x1="0" y1={y} x2="520" y2={y}
                stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
            ))}

            {/* Candles */}
            {CANDLE_DATA.map((bar, i) => {
              const scale = (v: number) => 125 - (v / 100) * 115;
              const x = 18 + i * 41;
              const bodyTop = scale(Math.max(bar.o, bar.c));
              const bodyBot = scale(Math.min(bar.o, bar.c));
              const bodyH = Math.max(bodyBot - bodyTop, 2);
              const color = bar.up ? "#10b981" : "#f43f5e";
              return (
                <g key={i} className="candle-group" style={{ animationDelay: `${i * 0.07}s` }}>
                  <line x1={x + 7} y1={scale(bar.h)} x2={x + 7} y2={scale(bar.l)}
                    stroke={color} strokeWidth="1.5" />
                  <rect x={x} y={bodyTop} width={14} height={bodyH}
                    fill={color} opacity="0.88" rx="1.5" />
                </g>
              );
            })}

            {/* Trend line overlay */}
            <polyline
              points="25,52 66,44 107,57 148,30 189,36 230,22 271,17 312,44 353,35 394,26 435,21 476,46"
              fill="none" stroke="#10b981" strokeWidth="1.5"
              strokeDasharray="6 4" opacity="0.35"
            />
          </svg>
        </div>

        {/* Market metrics row */}
        <div className="loader-metrics-row">
          {[
            { label: "S&P 500",  val: "5,648.40", delta: "+0.87%", up: true  },
            { label: "NASDAQ",   val: "19,944.22", delta: "+1.12%", up: true  },
            { label: "VIX",      val: "18.42",    delta: "-2.33%", up: false },
            { label: "10Y YILD", val: "4.21%",    delta: "-0.04",  up: false },
          ].map((m) => (
            <div key={m.label} className="loader-metric-tile">
              <span className="loader-metric-label">{m.label}</span>
              <span className={`loader-metric-val ${m.up ? "up" : "down"}`}>{m.val}</span>
              <span className={`loader-metric-delta ${m.up ? "up" : "down"}`}>{m.delta}</span>
            </div>
          ))}
        </div>

        {/* Boot / scan terminal */}
        <div className="loader-terminal">
          {SCAN_STEPS.slice(0, scanStep + 1).map((line, i) => (
            <div key={i} className={`scan-line ${i === scanStep ? "scan-line-active" : "scan-line-done"}`}>
              <span className="scan-prompt">&gt;&gt;</span>
              <span>{line}</span>
              {i === scanStep && i < SCAN_STEPS.length - 1 && <span className="boot-cursor" />}
              {i === scanStep && i === SCAN_STEPS.length - 1 && (
                <span className="scan-ok-tag">DISPATCHED</span>
              )}
            </div>
          ))}
        </div>

        {/* Infinite progress pulse */}
        <div className="loader-pulse-bar-wrap">
          <div className="loader-pulse-bar">
            <div className="loader-pulse-fill" />
          </div>
          <span className="loader-status-text">Autonomous agent running forensic playbook...</span>
        </div>

      </div>

      {/* ── BOTTOM SCROLLING TICKER TAPE (reverse) ── */}
      <div className="ticker-tape ticker-tape-bottom">
        <div className="ticker-track ticker-track-reverse">
          {[...TICKER_STREAM, ...TICKER_STREAM].map((t, i) => (
            <span key={i} className={`ticker-item ${t.up ? "tick-up" : "tick-down"}`}>
              <span className="tick-sym">{t.sym}</span>
              <span className="tick-price">{t.price}</span>
              <span className="tick-change">{t.change}</span>
              <span className="tick-sep">·</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
