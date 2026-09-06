import { writeFile, readFile, rename, access } from "node:fs/promises";
import { constants } from "node:fs";
import { dirname } from "node:path";
import { randomUUID } from "node:crypto";
import { Pool } from "pg";

export type StrategyState = Record<string, { disabled: boolean; reason: string; at: string }>;

export interface StrategyStore {
  /** Human-readable description of where state is kept, for tool responses. */
  readonly description: string;
  disable(symbol: string, reason: string): Promise<{ at: string }>;
  /**
   * Full current kill-switch state. This is the read side that the
   * `/strategy-state` HTTP endpoint exposes so the separately-built OAA
   * pipeline can poll it over HTTP instead of reading a local file —
   * the only integration path that works the same way regardless of
   * whether disable() is backed by Postgres or the local file fallback.
   *
   * Must reject on a real storage failure (permission error, corrupt data,
   * unreachable database) rather than resolving to `{}` — this is the
   * pre-scan kill-switch gate, so an empty-looking "success" response is
   * indistinguishable from "nothing is disabled" and would let OAA trade a
   * symbol it should be blocked from.
   */
  getState(): Promise<StrategyState>;
  /**
   * Cheap connectivity check used by GET /health. A store that can't
   * actually persist a disable shouldn't report healthy just because the
   * Node process is up — Render uses /health to decide whether to keep
   * routing traffic (and restart the service), so this needs to reflect
   * the real backend, not just process liveness.
   */
  checkHealth(): Promise<void>;
}

/**
 * Wraps a one-shot async initializer so concurrent callers share the same
 * in-flight attempt (no duplicate CREATE TABLE races), but a rejection is
 * NOT cached forever the way a plain `this.ready = init()` field would be —
 * once a JS promise rejects, awaiting it always rethrows the same error, so
 * a transient failure at construction time (e.g. the database briefly
 * unreachable at startup) would otherwise permanently poison every later
 * disable/getState/checkHealth call for the life of the process. Here, a
 * rejection clears the cached attempt so the *next* caller gets a fresh
 * try instead of the same dead promise.
 */
export function retryableInit(init: () => Promise<void>): () => Promise<void> {
  let pending: Promise<void> | null = null;
  return () => {
    if (!pending) {
      pending = init().catch((err) => {
        pending = null;
        throw err;
      });
    }
    return pending;
  };
}

/**
 * Structural check that a parsed JSON value actually matches StrategyState
 * (a plain object mapping symbols to well-formed disable records), so
 * `readExisting` doesn't cast a malformed-but-syntactically-valid file
 * (`null`, `[]`, `{"AAPL": {"disabled": "yes"}}`, ...) through as if it
 * were real state.
 */
function isStrategyState(value: unknown): value is StrategyState {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return false;
  }
  return Object.values(value).every(
    (entry) =>
      typeof entry === "object" &&
      entry !== null &&
      typeof (entry as { disabled?: unknown }).disabled === "boolean" &&
      typeof (entry as { reason?: unknown }).reason === "string" &&
      typeof (entry as { at?: unknown }).at === "string",
  );
}

/**
 * Local-file store. Fine for local development, where the process and its
 * working directory persist for the life of the session — but this must
 * never be the store used in the Render deployment: free web services have
 * an ephemeral filesystem and discard local writes on every restart,
 * redeploy, or spin-down, which would silently resurrect a "disabled"
 * strategy. See PostgresStrategyStore for the durable alternative.
 */
export class FileStrategyStore implements StrategyStore {
  readonly description: string;

  // Serializes disable() calls (and getState() reads) against this file.
  // Without this, two concurrent disables can both read the same on-disk
  // state before either writes and the second write clobbers the first
  // symbol's entry, and a getState() racing a disable() could observe a
  // half-written file. This promise is always swallowed to a resolution
  // (see the `.catch(() => {})` below), so awaiting it never throws — it
  // exists purely to sequence access, not to report a write's outcome.
  private writeQueue: Promise<unknown> = Promise.resolve();

  constructor(private readonly path: string) {
    this.description = path;
  }

  async disable(symbol: string, reason: string): Promise<{ at: string }> {
    const at = new Date().toISOString();
    const task = this.writeQueue.then(async () => {
      const state = await this.readExisting();
      state[symbol] = { disabled: true, reason, at };
      // Write atomically (temp file + rename) so a concurrent getState()
      // — or a crash mid-write — never observes a partially-written file.
      // rename() is atomic on the same filesystem, which a sibling temp
      // file in the same directory guarantees.
      const tmpPath = `${this.path}.${randomUUID()}.tmp`;
      await writeFile(tmpPath, JSON.stringify(state, null, 2));
      await rename(tmpPath, this.path);
    });
    // Keep the queue alive even if this write fails, so a failed disable
    // doesn't permanently wedge every disable()/getState() call after it;
    // the rejection itself still propagates to this caller via `await task`.
    this.writeQueue = task.catch(() => {});
    await task;
    return { at };
  }

  async getState(): Promise<StrategyState> {
    // Wait for any write currently queued or in-flight, so a read never
    // observes a half-written file (writeQueue is already error-swallowed
    // above, so this never throws on a prior write's behalf).
    await this.writeQueue;
    return this.readExisting();
  }

  private async readExisting(): Promise<StrategyState> {
    let raw: string;
    try {
      raw = await readFile(this.path, "utf8");
    } catch (err) {
      // A file that has genuinely never been written (nothing disabled
      // yet) is the ONLY case that legitimately means "empty". Anything
      // else — permission denied, a directory where a file was expected —
      // is a real storage failure and must propagate, not be swallowed
      // into a false-empty "nothing disabled" result.
      if ((err as NodeJS.ErrnoException).code === "ENOENT") return {};
      throw err;
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      throw new Error(`Corrupt strategy state file at ${this.path}: not valid JSON`);
    }

    // Valid JSON isn't necessarily a valid StrategyState — `null`, an
    // array, or an object with malformed entries would otherwise be cast
    // through as-is and either report a false-empty state or crash later
    // at `state[symbol] = ...`. Only a genuinely well-shaped object counts;
    // anything else is a corrupt-storage failure, same as bad JSON.
    if (!isStrategyState(parsed)) {
      throw new Error(`Corrupt strategy state file at ${this.path}: unexpected shape`);
    }
    return parsed;
  }

  async checkHealth(): Promise<void> {
    try {
      // File exists — confirm it's actually readable and writable rather
      // than just present (a permission error here means disable() and
      // getState() will fail too).
      await access(this.path, constants.R_OK | constants.W_OK);
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code !== "ENOENT") throw err;
      // Nothing disabled yet, so the file doesn't exist — healthy as long
      // as disable() would actually be able to create it, i.e. the parent
      // directory itself is writable.
      await access(dirname(this.path), constants.W_OK);
    }
  }
}

/**
 * Postgres-backed store. Durable across restarts, redeploys, and spin-downs,
 * which is what the Render deployment needs since its free web service
 * cannot attach a persistent disk (see render.yaml's `sentinel-strategy-state`
 * database and the `DATABASE_URL` env var wired into the mcp-server service).
 *
 * Note: Render's free Postgres plan is auto-deleted 30 days after creation.
 * That's a separate, milder limitation than the bug this fixes (the state
 * used to vanish on every restart/redeploy/spin-down; now it only needs
 * attention once a month). Recreate the database and update DATABASE_URL
 * before day 30, or upgrade the database to a paid plan, to avoid a gap.
 */
export class PostgresStrategyStore implements StrategyStore {
  readonly description = "the durable strategy_state table";

  private readonly pool: Pool;
  private readonly ready: () => Promise<void>;

  constructor(connectionString: string) {
    this.pool = new Pool({
      connectionString,
      // Fail fast instead of hanging: an unresponsive database should
      // surface as a normal rejected call (and a 503/502 at the HTTP
      // layer), not a request that never completes.
      connectionTimeoutMillis: 5_000,
      statement_timeout: 5_000,
    });
    // Required by the pg docs: an idle client can emit an error in the
    // background (e.g. the connection being dropped by the server), and
    // without this handler that crashes the whole process.
    this.pool.on("error", (err) => {
      console.error("Unexpected error on idle Postgres client:", err);
    });

    this.ready = retryableInit(() =>
      this.pool
        .query(
          `CREATE TABLE IF NOT EXISTS strategy_state (
             symbol TEXT PRIMARY KEY,
             disabled BOOLEAN NOT NULL,
             reason TEXT NOT NULL,
             at TIMESTAMPTZ NOT NULL
           )`,
        )
        .then(() => undefined),
    );
    // Kick off initialization eagerly so the common case (Postgres already
    // reachable) pays no extra latency on the first real call, without
    // leaving an unhandled rejection if it fails before anyone awaits it —
    // a later disable()/getState()/checkHealth() call will retry via
    // `this.ready()` regardless of whether this eager attempt succeeded.
    this.ready().catch(() => {});
  }

  async disable(symbol: string, reason: string): Promise<{ at: string }> {
    await this.ready();
    const at = new Date().toISOString();
    await this.pool.query(
      `INSERT INTO strategy_state (symbol, disabled, reason, at)
       VALUES ($1, true, $2, $3)
       ON CONFLICT (symbol) DO UPDATE SET disabled = true, reason = $2, at = $3`,
      [symbol, reason, at],
    );
    return { at };
  }

  async getState(): Promise<StrategyState> {
    await this.ready();
    const { rows } = await this.pool.query<{ symbol: string; disabled: boolean; reason: string; at: string | Date }>(
      `SELECT symbol, disabled, reason, at FROM strategy_state`,
    );
    const state: StrategyState = {};
    for (const row of rows) {
      state[row.symbol] = {
        disabled: row.disabled,
        reason: row.reason,
        at: row.at instanceof Date ? row.at.toISOString() : row.at,
      };
    }
    return state;
  }

  async checkHealth(): Promise<void> {
    await this.ready();
    await this.pool.query("SELECT 1");
  }
}

/**
 * Picks the durable Postgres store whenever DATABASE_URL is configured
 * (always true on Render, via render.yaml), and falls back to a local file
 * only when it isn't (local `npm run dev`, where no database is required).
 */
export function createStrategyStore(databaseUrl: string | undefined, filePath: string): StrategyStore {
  if (databaseUrl) {
    return new PostgresStrategyStore(databaseUrl);
  }
  return new FileStrategyStore(filePath);
}
