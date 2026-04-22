import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  AdminApiError,
  getCandidates,
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
      ok({ status: "ok", stories_added: 3 }),
    );
    const r = await runCollect();
    expect(r.stories_added).toBe(3);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/admin/devs/collect",
      expect.objectContaining({ method: "POST", cache: "no-store" }),
    );
  });

  it("runPublish posts to /publish", async () => {
    mockFetch.mockResolvedValueOnce(
      ok({ status: "published", feed_size: 5 }),
    );
    const r = await runPublish();
    expect(r.feed_size).toBe(5);
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/admin/devs/publish",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("getCandidates GETs /candidates", async () => {
    mockFetch.mockResolvedValueOnce(ok([]));
    await getCandidates();
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/api/admin/devs/candidates",
      expect.objectContaining({ cache: "no-store" }),
    );
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
