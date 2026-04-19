import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import BudgetPanel from "@/components/devs/admin/BudgetPanel";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockClear();
  vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
});

afterEach(() => {
  vi.useRealTimers();
});

function ok(data: unknown) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(""),
  };
}

describe("BudgetPanel", () => {
  it("fetches /budget on mount and renders the core stats", async () => {
    mockFetch.mockResolvedValueOnce(
      ok({
        tweets_used_30d: 1200,
        tweets_cap: 15000,
        pct_used: 8.0,
        remaining: 13800,
        will_pause_at: null,
      }),
    );

    render(<BudgetPanel />);

    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/admin/devs/budget",
        expect.objectContaining({ cache: "no-store" }),
      ),
    );
    expect(await screen.findByText("8.0%")).toBeInTheDocument();
    expect(screen.getByText("1,200")).toBeInTheDocument();
    expect(screen.getByText("15,000")).toBeInTheDocument();
    expect(screen.getByText("13,800")).toBeInTheDocument();
  });

  it("shows a paused alert when will_pause_at is present", async () => {
    mockFetch.mockResolvedValueOnce(
      ok({
        tweets_used_30d: 15000,
        tweets_cap: 15000,
        pct_used: 100,
        remaining: 0,
        will_pause_at: "2026-04-20T00:00:00Z",
      }),
    );

    render(<BudgetPanel />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/paused/i),
    );
  });

  it("refreshes every 60 seconds", async () => {
    mockFetch
      .mockResolvedValueOnce(
        ok({
          tweets_used_30d: 100,
          tweets_cap: 15000,
          pct_used: 0.6,
          remaining: 14900,
          will_pause_at: null,
        }),
      )
      .mockResolvedValueOnce(
        ok({
          tweets_used_30d: 200,
          tweets_cap: 15000,
          pct_used: 1.3,
          remaining: 14800,
          will_pause_at: null,
        }),
      );

    render(<BudgetPanel />);
    await screen.findByText("0.6%");

    await vi.advanceTimersByTimeAsync(60_000);

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("1.3%")).toBeInTheDocument();
  });

  it("renders an error banner on failure", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error("x")),
      text: () => Promise.resolve("kaboom"),
    });

    render(<BudgetPanel />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/kaboom/),
    );
  });
});
