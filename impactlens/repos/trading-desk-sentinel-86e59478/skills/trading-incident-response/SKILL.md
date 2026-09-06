---
name: trading-incident-response
description: Playbook for investigating an anomaly (drawdown, unexpected position, risk-limit breach) in the OAA paper-trading account before proposing any irreversible action.
---

# Trading Incident Response

Use this skill whenever asked to investigate an account anomaly, alert, or
"why did X happen" question about the paper-trading account. Follow the
steps in order — do not skip to a conclusion or an action.

## 1. Establish the current state

Call `get_account`. Compare `equity` to `last_equity` to size the move.
Note `buying_power` — a large unexplained drop there, with equity flat,
usually means an order is open and unfilled, not a loss.

## 2. Locate the anomaly in time

Call `get_portfolio_history` (start with `period=1M`, `timeframe=1D`; narrow
to `period=1W`, `timeframe=15Min` once you have a rough date). Use the
sandbox to compute day-over-day percent change on the returned equity
series — do not eyeball it. Find the first timestamp where the drop
exceeds what a single normal trade would explain.

## 3. Find the responsible fill(s)

Call `get_recent_orders` with a `limit` generous enough to cover the window
around that timestamp. In the sandbox, join order fill times against the
equity-curve breakpoint from step 2 — the order(s) filled in the minutes
immediately before the break are your candidates.

## 4. Check current exposure

Call `get_positions`. For each position tied to a candidate order, note
size and unrealized P&L. This tells you whether the anomaly is still
"live" (an open position still moving) or already resolved (a closed
trade that already realized its loss).

## 5. State root cause before proposing anything

Write one or two sentences: which symbol, which order(s), what the
mechanism was (e.g. "a bear-call spread was assigned early," "a stop
was never attached and the position rode a 4% reversal," "buying power
dropped because two orders double-filled on a reconnect"). If the
evidence doesn't support a specific mechanism, say the investigation is
inconclusive — do not paper over uncertainty with a plausible-sounding
guess.

## 6. Only then, consider an action

- `flatten_position` — only if the position is still open and the root
  cause implies it should not be held further.
- `disable_strategy` — only if the root cause is a strategy-level defect
  (not a one-off), and only for the specific symbol implicated, not the
  whole watchlist, unless the evidence points to a systemic cause.

Both tools are approval-gated by the harness. State your recommendation
and reasoning in the message immediately before calling either — the
human approving needs your root-cause statement, not just the tool call,
to make an informed decision.

## What not to do

- Do not call `flatten_position` or `disable_strategy` as a precaution
  "just in case." Every call must trace to a stated root cause.
- Do not skip `get_portfolio_history` and go straight to guessing from
  `get_positions` alone — you'll miss anomalies that already resolved.
- Do not estimate percentages or do date arithmetic in your head when the
  sandbox is available — compute it.
