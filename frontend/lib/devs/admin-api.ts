// TODO: add basic auth header once infra protects /devs/admin publicly.

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE = `${API_URL}/api/admin/devs`;

export interface CollectResponse {
  status: "ok" | "error";
  stories_added: number;
  videos_added: number;
}

export interface PublishResponse {
  status: "published" | "skipped";
  feed_size: number;
  digest_title: string;
}

export interface Candidate {
  id: number;
  source: "hn" | "github";
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
