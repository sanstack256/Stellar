import { describe, it, expect, afterEach } from "vitest";
import { readFile, rm, mkdir, chmod, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import { createStrategyStore, FileStrategyStore, PostgresStrategyStore, retryableInit } from "./strategy-store.js";

describe("createStrategyStore", () => {
  it("falls back to a FileStrategyStore when no DATABASE_URL is given", () => {
    const store = createStrategyStore(undefined, "./strategy_state.json");
    expect(store).toBeInstanceOf(FileStrategyStore);
  });

  it("chooses PostgresStrategyStore whenever a DATABASE_URL is given, so Render deploys never fall back to the ephemeral filesystem", () => {
    const store = createStrategyStore("postgres://user:pass@host/db", "./strategy_state.json");
    expect(store).toBeInstanceOf(PostgresStrategyStore);
    expect(store.description).toBe("the durable strategy_state table");
  });
});

// Regression coverage for the Qodo finding "Initialization failure never
// recovers": exercises the exact retry contract PostgresStrategyStore
// depends on, without needing a live database — a failed init must not be
// cached forever, and concurrent callers during a single attempt must
// share it rather than firing the initializer multiple times.
describe("retryableInit", () => {
  it("shares one in-flight attempt across concurrent callers", async () => {
    let calls = 0;
    const ready = retryableInit(async () => {
      calls += 1;
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    await Promise.all([ready(), ready(), ready()]);
    expect(calls).toBe(1);
  });

  it("retries on the next call after a rejection, instead of caching it forever", async () => {
    let calls = 0;
    const ready = retryableInit(async () => {
      calls += 1;
      if (calls === 1) throw new Error("transient outage");
    });

    await expect(ready()).rejects.toThrow("transient outage");
    // A plain `this.ready = init()` field would still be rejected here —
    // this is the behavior that was broken.
    await expect(ready()).resolves.toBeUndefined();
    expect(calls).toBe(2);
  });
});

describe("FileStrategyStore", () => {
  const path = join(tmpdir(), `strategy-state-${randomUUID()}.json`);

  afterEach(async () => {
    await rm(path, { force: true });
  });

  it("creates the file on first disable and records disabled/reason/at", async () => {
    const store = new FileStrategyStore(path);
    const { at } = await store.disable("SPY", "unexplained drawdown");

    const written = JSON.parse(await readFile(path, "utf8"));
    expect(written).toEqual({ SPY: { disabled: true, reason: "unexplained drawdown", at } });
  });

  it("merges into existing entries instead of clobbering other symbols", async () => {
    const store = new FileStrategyStore(path);
    await store.disable("SPY", "first reason");
    await store.disable("QQQ", "second reason");

    const written = JSON.parse(await readFile(path, "utf8"));
    expect(Object.keys(written).sort()).toEqual(["QQQ", "SPY"]);
    expect(written.SPY.reason).toBe("first reason");
    expect(written.QQQ.reason).toBe("second reason");
  });

  it("getState reflects what disable() just wrote, for the /strategy-state poller", async () => {
    const store = new FileStrategyStore(path);
    await store.disable("SPY", "unexplained drawdown");

    const state = await store.getState();
    expect(state.SPY).toMatchObject({ disabled: true, reason: "unexplained drawdown" });
  });

  it("getState returns an empty object when nothing has ever been disabled (file genuinely absent)", async () => {
    const store = new FileStrategyStore(path);
    expect(await store.getState()).toEqual({});
  });

  // Regression coverage for the Qodo finding "File reads fail open": a file
  // that exists but is corrupt must surface as an error, not as "nothing is
  // disabled" — the latter would let /strategy-state report a disabled
  // symbol as tradeable again.
  it("getState propagates a JSON parse failure instead of reporting an empty (fail-open) state", async () => {
    await writeFile(path, "{ not valid json");
    const store = new FileStrategyStore(path);
    await expect(store.getState()).rejects.toThrow();
  });

  // Regression coverage for the Qodo finding "Invalid state shape
  // succeeds": syntactically valid JSON that isn't a well-formed
  // StrategyState (null, an array, or entries with the wrong field types)
  // must surface as a storage failure, not a false-empty or corrupt state
  // that later crashes disable() at `state[symbol] = ...`.
  it.each([
    ["null", "null"],
    ["an array", "[]"],
    ["a non-object entry", JSON.stringify({ SPY: "disabled" })],
    ["an entry with the wrong field types", JSON.stringify({ SPY: { disabled: "yes", reason: "x", at: "x" } })],
  ])("getState rejects when the file contains %s instead of a valid StrategyState", async (_label, contents) => {
    await writeFile(path, contents);
    const store = new FileStrategyStore(path);
    await expect(store.getState()).rejects.toThrow(/unexpected shape/);
  });

  it("writes atomically, so a reader never observes a partially-written file", async () => {
    const store = new FileStrategyStore(path);
    await store.disable("SPY", "reason");
    // No leftover .tmp file after a successful write.
    const written = JSON.parse(await readFile(path, "utf8"));
    expect(written.SPY.disabled).toBe(true);
  });

  it("serializes concurrent disables instead of losing one to a read-modify-write race", async () => {
    const store = new FileStrategyStore(path);

    // Fire both disables without awaiting the first, so their read-modify-write
    // cycles would overlap absent the internal write queue.
    await Promise.all([store.disable("SPY", "reason A"), store.disable("QQQ", "reason B")]);

    const written = JSON.parse(await readFile(path, "utf8"));
    expect(Object.keys(written).sort()).toEqual(["QQQ", "SPY"]);
    expect(written.SPY.reason).toBe("reason A");
    expect(written.QQQ.reason).toBe("reason B");
  });

  // Regression coverage for the Qodo finding "File health ignores failures".
  describe("checkHealth", () => {
    it("resolves when nothing has been disabled yet but the parent directory is writable", async () => {
      const store = new FileStrategyStore(path);
      await expect(store.checkHealth()).resolves.toBeUndefined();
    });

    it("resolves once the file exists and is readable/writable", async () => {
      const store = new FileStrategyStore(path);
      await store.disable("SPY", "reason");
      await expect(store.checkHealth()).resolves.toBeUndefined();
    });

    it("rejects when the configured path's parent directory doesn't exist", async () => {
      const missingDir = join(tmpdir(), `no-such-dir-${randomUUID()}`, "strategy_state.json");
      const store = new FileStrategyStore(missingDir);
      await expect(store.checkHealth()).rejects.toThrow();
    });

    it("rejects when the file exists but isn't writable", async () => {
      // Skip under a root-run CI container: root bypasses permission bits,
      // so chmod 0o444 wouldn't actually block the write and this
      // assertion would be meaningless there rather than false-negative.
      if (typeof process.getuid === "function" && process.getuid() === 0) return;

      const roDir = join(tmpdir(), `sentinel-ro-${randomUUID()}`);
      await mkdir(roDir);
      const roPath = join(roDir, "strategy_state.json");
      await writeFile(roPath, "{}");
      await chmod(roPath, 0o444);
      const store = new FileStrategyStore(roPath);
      try {
        await expect(store.checkHealth()).rejects.toThrow();
      } finally {
        await chmod(roPath, 0o644);
        await rm(roDir, { recursive: true, force: true });
      }
    });
  });
});
