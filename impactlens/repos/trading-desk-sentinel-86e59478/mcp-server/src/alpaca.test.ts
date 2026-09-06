import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const ORIGINAL_ENV = { ...process.env };

describe("alpaca.ts", () => {
  beforeEach(() => {
    process.env.ALPACA_API_KEY = "test-key";
    process.env.ALPACA_SECRET_KEY = "test-secret";
    process.env.ALPACA_BASE_URL = "https://paper-api.alpaca.markets";
    vi.resetModules();
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.restoreAllMocks();
  });

  it("getAccount sends the correct auth headers and path", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ equity: "98150.00", last_equity: "102340.00" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getAccount } = await import("./alpaca.js");
    const account = await getAccount();

    expect(fetchMock).toHaveBeenCalledWith(
      "https://paper-api.alpaca.markets/v2/account",
      expect.objectContaining({
        headers: expect.objectContaining({
          "APCA-API-KEY-ID": "test-key",
          "APCA-API-SECRET-KEY": "test-secret",
        }),
      }),
    );
    expect(account).toEqual({ equity: "98150.00", last_equity: "102340.00" });
  });

  it("throws with the response body when Alpaca returns a non-OK status", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      text: async () => '{"code":40110000,"message":"forbidden"}',
    });
    vi.stubGlobal("fetch", fetchMock);

    const { getPositions } = await import("./alpaca.js");
    await expect(getPositions()).rejects.toThrow(/403/);
  });

  it("throws a clear error when credentials are missing, before ever calling fetch", async () => {
    delete process.env.ALPACA_API_KEY;
    delete process.env.ALPACA_SECRET_KEY;
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const { getAccount } = await import("./alpaca.js");
    await expect(getAccount()).rejects.toThrow(/ALPACA_API_KEY/);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("flattenPosition issues a DELETE to the correct encoded position path", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "filled", symbol: "SPY" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { flattenPosition } = await import("./alpaca.js");
    await flattenPosition("SPY");

    expect(fetchMock).toHaveBeenCalledWith(
      "https://paper-api.alpaca.markets/v2/positions/SPY",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("never targets a live-trading host regardless of how ALPACA_BASE_URL is set", async () => {
    delete process.env.ALPACA_BASE_URL;
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", fetchMock);

    const { getAccount } = await import("./alpaca.js");
    await getAccount();

    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(new URL(calledUrl).hostname).toBe("paper-api.alpaca.markets");
    expect(new URL(calledUrl).hostname).not.toBe("api.alpaca.markets"); // the live-trading host
  });

  it("rejects non-paper ALPACA_BASE_URL overrides before making a request", async () => {
    process.env.ALPACA_BASE_URL = "https://api.alpaca.markets";
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    await expect(import("./alpaca.js")).rejects.toThrow(/Only the Alpaca paper-trading endpoint/);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
