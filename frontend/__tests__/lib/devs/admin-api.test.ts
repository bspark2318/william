import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  AdminApiError,
  addDiscoveredHandle,
  getBudget,
  getCandidates,
  getDiscoveredHandles,
  getHandleStats,
  ignoreDiscoveredHandle,
  runCollect,
  runPublish,
} from "@/lib/devs/admin-api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => mockFetch.mockClear());

function ok(data: unknown) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  };
}

function fail(status: number, body: string) {
  return {
    ok: false,
    status,
    json: () => Promise.reject(new Error("no json")),
    text: () => Promise.resolve(body),
  };
}

describe("admin-api", () => {
  it("runCollect posts to /collect and returns payload", async () => {
    mockFetch.mockResolvedValueOnce(
      ok({ status: "ok", stories_added: 3, videos_added: 0, tweets_added: 42 }),
    );
    const r = await runCollect();
    expect(r.stories_added).toBe(3);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/admin-proxy/devs/collect",
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
  });

  it("runPublish posts to /publish", async () => {
    mockFetch.mockResolvedValueOnce(
      ok({ status: "published", feed_size: 8, digest_title: "t" }),
    );
    const r = await runPublish();
    expect(r.feed_size).toBe(8);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/admin-proxy/devs/publish",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("getCandidates GETs /candidates", async () => {
    mockFetch.mockResolvedValueOnce(ok([]));
    await getCandidates();
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/admin-proxy/devs/candidates",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("getHandleStats GETs /handle-stats", async () => {
    mockFetch.mockResolvedValueOnce(ok([]));
    await getHandleStats();
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/admin-proxy/devs/handle-stats",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("getDiscoveredHandles defaults to status=pending", async () => {
    mockFetch.mockResolvedValueOnce(ok([]));
    await getDiscoveredHandles();
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/admin-proxy/devs/discovered-handles?status=pending",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("addDiscoveredHandle url-encodes the handle", async () => {
    mockFetch.mockResolvedValueOnce(ok({ status: "added" }));
    await addDiscoveredHandle("weird name");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/admin-proxy/devs/discovered-handles/weird%20name/add",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("ignoreDiscoveredHandle posts to /ignore", async () => {
    mockFetch.mockResolvedValueOnce(ok({ status: "ignored" }));
    await ignoreDiscoveredHandle("foo");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/admin-proxy/devs/discovered-handles/foo/ignore",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("getBudget GETs /budget", async () => {
    mockFetch.mockResolvedValueOnce(
      ok({
        tweets_used_30d: 100,
        tweets_cap: 15000,
        pct_used: 0.6,
        remaining: 14900,
        will_pause_at: null,
      }),
    );
    const b = await getBudget();
    expect(b.tweets_cap).toBe(15000);
  });

  it("throws AdminApiError on non-ok responses with body", async () => {
    mockFetch.mockResolvedValueOnce(fail(500, "boom"));
    await expect(runCollect()).rejects.toBeInstanceOf(AdminApiError);
    mockFetch.mockResolvedValueOnce(fail(502, "upstream"));
    try {
      await runPublish();
      throw new Error("expected throw");
    } catch (e) {
      expect(e).toBeInstanceOf(AdminApiError);
      expect((e as AdminApiError).status).toBe(502);
      expect((e as AdminApiError).body).toBe("upstream");
    }
  });
});
