import { act, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import HandleManagement from "@/components/devs/admin/HandleManagement";
import type {
  DiscoveredHandle,
  HandleStat,
} from "@/lib/devs/admin-api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => mockFetch.mockClear());

function ok(data: unknown) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(""),
  };
}

function stat(overrides: Partial<HandleStat> = {}): HandleStat {
  return {
    handle: "default",
    tweets_collected_30d: 10,
    tweets_scored_above_6_30d: 5,
    tweets_published_30d: 2,
    last_published_at: "2026-04-10T00:00:00Z",
    ...overrides,
  };
}

function disc(overrides: Partial<DiscoveredHandle> = {}): DiscoveredHandle {
  return {
    handle: "newbie",
    first_seen_at: "2026-04-15T00:00:00Z",
    last_seen_at: "2026-04-17T00:00:00Z",
    seed_engagement_count: 4,
    seed_handles: ["karpathy", "simonw"],
    status: "pending",
    ...overrides,
  };
}

describe("HandleManagement", () => {
  it("loads both tables and renders rows", async () => {
    mockFetch
      .mockResolvedValueOnce(
        ok([
          stat({ handle: "karpathy", tweets_published_30d: 4 }),
          stat({
            handle: "deadweight",
            tweets_published_30d: 0,
            last_published_at: null,
          }),
        ]),
      )
      .mockResolvedValueOnce(ok([disc({ handle: "newbie" })]));

    render(<HandleManagement />);

    await screen.findByText("@karpathy");
    expect(screen.getByText("@deadweight")).toBeInTheDocument();
    expect(screen.getByText("@newbie")).toBeInTheDocument();
  });

  it("flags dead-weight handles (0 published)", async () => {
    mockFetch
      .mockResolvedValueOnce(
        ok([
          stat({ handle: "deadweight", tweets_published_30d: 0 }),
          stat({ handle: "active", tweets_published_30d: 3 }),
        ]),
      )
      .mockResolvedValueOnce(ok([]));

    const { container } = render(<HandleManagement />);
    await screen.findByText("@deadweight");

    const deadRow = container.querySelector('tr[data-dead="true"]');
    expect(deadRow).not.toBeNull();
    expect(within(deadRow as HTMLElement).getByText("@deadweight")).toBeInTheDocument();
  });

  it("sorts active table when a column header is clicked", async () => {
    mockFetch
      .mockResolvedValueOnce(
        ok([
          stat({ handle: "a", tweets_collected_30d: 1 }),
          stat({ handle: "b", tweets_collected_30d: 99 }),
        ]),
      )
      .mockResolvedValueOnce(ok([]));

    render(<HandleManagement />);
    await screen.findByText("@a");

    await act(async () => {
      screen.getByRole("button", { name: /collected 30d/i }).click();
    });

    const rows = screen.getAllByRole("row");
    // row 0 is thead; data rows follow
    const firstDataRow = rows[1];
    expect(within(firstDataRow).getByText("@a")).toBeInTheDocument();

    await act(async () => {
      screen.getByRole("button", { name: /collected 30d/i }).click();
    });

    const rows2 = screen.getAllByRole("row");
    expect(within(rows2[1]).getByText("@b")).toBeInTheDocument();
  });

  it("calls /add and removes the row on success", async () => {
    mockFetch
      .mockResolvedValueOnce(ok([]))
      .mockResolvedValueOnce(ok([disc({ handle: "newbie" })]))
      .mockResolvedValueOnce(ok({ status: "added" }));

    render(<HandleManagement />);
    await screen.findByText("@newbie");

    await act(async () => {
      screen.getByRole("button", { name: /^add$/i }).click();
    });

    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/admin/devs/discovered-handles/newbie/add",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(screen.queryByText("@newbie")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/added/);
  });

  it("shows a toast when /add is rejected (cap hit) and keeps the row", async () => {
    mockFetch
      .mockResolvedValueOnce(ok([]))
      .mockResolvedValueOnce(ok([disc({ handle: "newbie" })]))
      .mockResolvedValueOnce(
        ok({ status: "rejected", reason: "MAX_X_HANDLES reached" }),
      );

    render(<HandleManagement />);
    await screen.findByText("@newbie");

    await act(async () => {
      screen.getByRole("button", { name: /^add$/i }).click();
    });

    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(/rejected/),
    );
    expect(screen.getByText("@newbie")).toBeInTheDocument();
  });

  it("optimistically removes a row on /ignore and shows a toast", async () => {
    mockFetch
      .mockResolvedValueOnce(ok([]))
      .mockResolvedValueOnce(ok([disc({ handle: "newbie" })]))
      .mockResolvedValueOnce(ok({ status: "ignored" }));

    render(<HandleManagement />);
    await screen.findByText("@newbie");

    await act(async () => {
      screen.getByRole("button", { name: /^ignore$/i }).click();
    });

    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/admin/devs/discovered-handles/newbie/ignore",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(screen.queryByText("@newbie")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/ignored/);
  });

  it("shows an error banner if handle-stats fails", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error("x")),
        text: () => Promise.resolve("backend dead"),
      })
      .mockResolvedValueOnce(ok([]));

    render(<HandleManagement />);
    await waitFor(() => {
      const alerts = screen.getAllByRole("alert");
      expect(alerts.some((a) => a.textContent?.includes("backend dead"))).toBe(
        true,
      );
    });
  });
});
