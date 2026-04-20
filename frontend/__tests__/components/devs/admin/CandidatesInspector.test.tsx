import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CandidatesInspector from "@/components/devs/admin/CandidatesInspector";
import type { Candidate } from "@/lib/devs/admin-api";

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

function cand(overrides: Partial<Candidate> = {}): Candidate {
  return {
    id: 1,
    source: "hn",
    title: "Default title",
    text: null,
    url: "https://example.com/a",
    importance_score: 5.2,
    rank_score: 7.1,
    rank_features: { a: 1 },
    collected_at: "2026-04-18T10:00:00Z",
    is_active: false,
    display_order: null,
    ...overrides,
  };
}

describe("CandidatesInspector", () => {
  it("fetches /candidates on mount and renders rows", async () => {
    mockFetch.mockResolvedValueOnce(
      ok([
        cand({ id: 1, title: "HN one" }),
        cand({ id: 2, source: "x", title: null, text: "X tweet body" }),
      ]),
    );

    render(<CandidatesInspector />);

    await waitFor(() =>
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/admin/devs/candidates",
        expect.objectContaining({ cache: "no-store" }),
      ),
    );
    expect(await screen.findByText("HN one")).toBeInTheDocument();
    expect(screen.getByText("X tweet body")).toBeInTheDocument();
  });

  it("filters by source when chip is clicked", async () => {
    mockFetch.mockResolvedValueOnce(
      ok([
        cand({ id: 1, source: "hn", title: "HN story" }),
        cand({ id: 2, source: "x", title: null, text: "tweet body" }),
        cand({ id: 3, source: "github", title: "gh release" }),
      ]),
    );

    render(<CandidatesInspector />);
    await screen.findByText("HN story");

    await act(async () => {
      screen.getByRole("button", { name: /^x$/i, pressed: false }).click();
    });

    expect(screen.queryByText("HN story")).not.toBeInTheDocument();
    expect(screen.queryByText("gh release")).not.toBeInTheDocument();
    expect(screen.getByText("tweet body")).toBeInTheDocument();
  });

  it("respects the 'active only' toggle", async () => {
    mockFetch.mockResolvedValueOnce(
      ok([
        cand({ id: 1, title: "inactive one", is_active: false }),
        cand({
          id: 2,
          title: "active one",
          is_active: true,
          display_order: 1,
        }),
      ]),
    );

    render(<CandidatesInspector />);
    await screen.findByText("inactive one");

    await act(async () => {
      screen.getByLabelText(/active only/i).click();
    });

    expect(screen.queryByText("inactive one")).not.toBeInTheDocument();
    expect(screen.getByText("active one")).toBeInTheDocument();
  });

  it("expands a row to reveal rank_features JSON", async () => {
    mockFetch.mockResolvedValueOnce(
      ok([
        cand({
          id: 42,
          title: "expandable",
          rank_features: { heuristic: 3.4, tier: "A" },
        }),
      ]),
    );

    render(<CandidatesInspector />);
    await screen.findByText("expandable");

    await act(async () => {
      screen.getByLabelText("expand row").click();
    });

    expect(screen.getByText(/rank_features/i)).toBeInTheDocument();
    expect(screen.getByText(/heuristic/)).toBeInTheDocument();
  });

  it("renders an error banner when the fetch fails", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: () => Promise.reject(new Error("x")),
      text: () => Promise.resolve("down for maintenance"),
    });

    render(<CandidatesInspector />);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(/503/),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/down for maintenance/);
  });
});
