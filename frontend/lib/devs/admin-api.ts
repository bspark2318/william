// Admin calls go through /app/api/admin-proxy/[...path]/route.ts, which
// injects the ADMIN_API_TOKEN server-side so it never reaches the browser.
const BASE = "/api/admin-proxy/devs";

export interface CollectResponse {
  status: "ok" | "error";
  stories_added: number;
  videos_added: number;
  tweets_added: number;
}

export interface PublishResponse {
  status: "published" | "skipped";
  feed_size: number;
  digest_title: string;
}

export interface Candidate {
  id: number;
  source: "x" | "hn" | "github";
  title?: string | null;
  text?: string | null;
  url: string;
  importance_score: number | null;
  rank_score: number | null;
  rank_features: Record<string, unknown> | null;
  collected_at: string;
  is_active: boolean;
  display_order: number | null;
}

export interface HandleStat {
  handle: string;
  tweets_collected_30d: number;
  tweets_scored_above_6_30d: number;
  tweets_published_30d: number;
  last_published_at: string | null;
}

export interface DiscoveredHandle {
  handle: string;
  first_seen_at: string;
  last_seen_at: string;
  seed_engagement_count: number;
  seed_handles: string[];
  status: "pending" | "added" | "ignored";
}

export interface AddHandleResponse {
  status: "added" | "rejected";
  reason?: string;
}

export interface IgnoreHandleResponse {
  status: "ignored";
}

export interface Budget {
  tweets_used_30d: number;
  tweets_cap: number;
  pct_used: number;
  remaining: number;
  will_pause_at: string | null;
}

export class AdminApiError extends Error {
  status: number;
  body: string;
  constructor(status: number, body: string) {
    super(`Admin API ${status}: ${body || "(empty response body)"}`);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store", ...init });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new AdminApiError(res.status, body);
  }
  return res.json();
}

export function runCollect(): Promise<CollectResponse> {
  return request("/collect", { method: "POST" });
}

export function runPublish(): Promise<PublishResponse> {
  return request("/publish", { method: "POST" });
}

export function getCandidates(): Promise<Candidate[]> {
  return request("/candidates");
}

export function getHandleStats(): Promise<HandleStat[]> {
  return request("/handle-stats");
}

export function getDiscoveredHandles(
  status: "pending" | "added" | "ignored" = "pending",
): Promise<DiscoveredHandle[]> {
  return request(`/discovered-handles?status=${encodeURIComponent(status)}`);
}

export function addDiscoveredHandle(
  handle: string,
): Promise<AddHandleResponse> {
  return request(`/discovered-handles/${encodeURIComponent(handle)}/add`, {
    method: "POST",
  });
}

export function ignoreDiscoveredHandle(
  handle: string,
): Promise<IgnoreHandleResponse> {
  return request(`/discovered-handles/${encodeURIComponent(handle)}/ignore`, {
    method: "POST",
  });
}

export function getBudget(): Promise<Budget> {
  return request("/budget");
}
