import { describe, it, expect, vi, beforeEach } from "vitest";
import { getIssues, getIssue, getLatestIssue } from "@/lib/api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => mockFetch.mockClear());

function jsonResponse(data: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(data) };
}

describe("getIssues", () => {
  it("fetches the issues list from the API", async () => {
    const issues = [{ id: 1, week_of: "2026-04-07", title: "Issue 1" }];
    mockFetch.mockResolvedValueOnce(jsonResponse(issues));

    const result = await getIssues();
    expect(result).toEqual(issues);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/issues",
      expect.objectContaining({ next: { revalidate: 60 } }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(null, 500));
    await expect(getIssues()).rejects.toThrow("Failed to fetch issues: 500");
  });
});

describe("getIssue", () => {
  it("fetches a single issue by id", async () => {
    const issue = { id: 3, week_of: "2026-04-07", title: "Issue 3", stories: [], featured_video: null };
    mockFetch.mockResolvedValueOnce(jsonResponse(issue));

    const result = await getIssue(3);
    expect(result).toEqual(issue);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/issues/3",
      expect.objectContaining({ next: { revalidate: 60 } }),
    );
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse(null, 404));
    await expect(getIssue(99)).rejects.toThrow("Failed to fetch issue 99: 404");
  });
});

describe("getLatestIssue", () => {
  it("fetches the first issue from the list", async () => {
    const issues = [
      { id: 5, week_of: "2026-04-07", title: "Latest" },
      { id: 4, week_of: "2026-03-31", title: "Older" },
    ];
    const fullIssue = { ...issues[0], stories: [], featured_video: null };

    mockFetch
      .mockResolvedValueOnce(jsonResponse(issues))
      .mockResolvedValueOnce(jsonResponse(fullIssue));

    const result = await getLatestIssue();
    expect(result).toEqual(fullIssue);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("throws when no issues exist", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse([]));
    await expect(getLatestIssue()).rejects.toThrow("No issues found");
  });
});
