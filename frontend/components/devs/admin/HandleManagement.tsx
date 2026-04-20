"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AdminApiError,
  DiscoveredHandle,
  HandleStat,
  addDiscoveredHandle,
  getDiscoveredHandles,
  getHandleStats,
  ignoreDiscoveredHandle,
} from "@/lib/devs/admin-api";
import ErrorBanner from "./ErrorBanner";

type StatKey =
  | "handle"
  | "tweets_collected_30d"
  | "tweets_scored_above_6_30d"
  | "tweets_published_30d"
  | "last_published_at";

export default function HandleManagement() {
  return (
    <div className="space-y-8">
      <ActiveHandlesTable />
      <DiscoveredHandlesTable />
    </div>
  );
}

function ActiveHandlesTable() {
  const [data, setData] = useState<HandleStat[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sort, setSort] = useState<{ key: StatKey; dir: "asc" | "desc" }>({
    key: "tweets_published_30d",
    dir: "asc",
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const rows = await getHandleStats();
        if (!cancelled) setData(rows);
      } catch (e) {
        if (!cancelled) setError(formatError(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const sorted = useMemo(() => {
    if (!data) return [];
    const copy = [...data];
    copy.sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (av === null && bv === null) return 0;
      if (av === null) return 1;
      if (bv === null) return -1;
      if (av < bv) return sort.dir === "asc" ? -1 : 1;
      if (av > bv) return sort.dir === "asc" ? 1 : -1;
      return 0;
    });
    return copy;
  }, [data, sort]);

  function toggleSort(key: StatKey) {
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "asc" },
    );
  }

  return (
    <section className="space-y-3">
      <h3 className="text-xs uppercase tracking-widest text-[#d4d4d8]">
        <span className="text-[#7cffb2]">#</span> active handles
      </h3>
      {error && <ErrorBanner message={error} />}
      {loading && (
        <p className="text-xs text-[#71717a] font-mono">
          loading handle stats…
        </p>
      )}
      {data && !error && (
        <div className="overflow-x-auto border border-[#1f2329] rounded">
          <table className="w-full text-xs font-mono">
            <thead className="bg-[#0e1115] text-[#71717a] uppercase tracking-widest">
              <tr>
                <StatHeader
                  label="handle"
                  k="handle"
                  sort={sort}
                  onClick={toggleSort}
                />
                <StatHeader
                  label="collected 30d"
                  k="tweets_collected_30d"
                  sort={sort}
                  onClick={toggleSort}
                  align="right"
                />
                <StatHeader
                  label="scored 6+"
                  k="tweets_scored_above_6_30d"
                  sort={sort}
                  onClick={toggleSort}
                  align="right"
                />
                <StatHeader
                  label="published 30d"
                  k="tweets_published_30d"
                  sort={sort}
                  onClick={toggleSort}
                  align="right"
                />
                <StatHeader
                  label="last published"
                  k="last_published_at"
                  sort={sort}
                  onClick={toggleSort}
                />
              </tr>
            </thead>
            <tbody>
              {sorted.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-3 py-6 text-center text-[#52525b]"
                  >
                    no active handles
                  </td>
                </tr>
              ) : (
                sorted.map((h) => {
                  const dead = h.tweets_published_30d === 0;
                  return (
                    <tr
                      key={h.handle}
                      data-dead={dead ? "true" : undefined}
                      className={`border-t border-[#1f2329] ${
                        dead ? "bg-red-500/5" : "hover:bg-[#0e1115]"
                      }`}
                    >
                      <td className="px-3 py-2 text-[#d4d4d8]">
                        @{h.handle}
                      </td>
                      <td className="px-3 py-2 text-right text-[#a1a1aa]">
                        {h.tweets_collected_30d}
                      </td>
                      <td className="px-3 py-2 text-right text-[#a1a1aa]">
                        {h.tweets_scored_above_6_30d}
                      </td>
                      <td
                        className={`px-3 py-2 text-right ${
                          dead ? "text-red-400" : "text-[#a1a1aa]"
                        }`}
                      >
                        {h.tweets_published_30d}
                      </td>
                      <td className="px-3 py-2 text-[#71717a]">
                        {h.last_published_at
                          ? new Date(h.last_published_at).toLocaleDateString()
                          : "—"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-[11px] text-[#52525b] font-mono">
        to drop a handle, edit <code>devs_config.yaml</code> manually.
      </p>
    </section>
  );
}

function StatHeader({
  label,
  k,
  sort,
  onClick,
  align = "left",
}: {
  label: string;
  k: StatKey;
  sort: { key: StatKey; dir: "asc" | "desc" };
  onClick: (k: StatKey) => void;
  align?: "left" | "right";
}) {
  const active = sort.key === k;
  const arrow = active ? (sort.dir === "asc" ? "↑" : "↓") : "";
  return (
    <th
      className={`px-3 py-2 text-${align}`}
      aria-sort={
        active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"
      }
    >
      <button
        type="button"
        onClick={() => onClick(k)}
        className={`uppercase tracking-widest ${
          active ? "text-[#d4d4d8]" : "hover:text-[#d4d4d8]"
        }`}
      >
        {label} {arrow}
      </button>
    </th>
  );
}

function DiscoveredHandlesTable() {
  const [data, setData] = useState<DiscoveredHandle[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await getDiscoveredHandles("pending");
      setData(rows);
    } catch (e) {
      setError(formatError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onAdd(handle: string) {
    setBusy(handle);
    setToast(null);
    try {
      const res = await addDiscoveredHandle(handle);
      if (res.status === "rejected") {
        setToast(`rejected: ${res.reason ?? "unknown reason"}`);
      } else {
        setToast(`@${handle} added`);
        setData((prev) => prev?.filter((h) => h.handle !== handle) ?? null);
      }
    } catch (e) {
      setToast(formatError(e));
    } finally {
      setBusy(null);
    }
  }

  async function onIgnore(handle: string) {
    setBusy(handle);
    setToast(null);
    const prevData = data;
    setData((prev) => prev?.filter((h) => h.handle !== handle) ?? null);
    try {
      await ignoreDiscoveredHandle(handle);
      setToast(`@${handle} ignored`);
    } catch (e) {
      setData(prevData);
      setToast(formatError(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="space-y-3">
      <h3 className="text-xs uppercase tracking-widest text-[#d4d4d8]">
        <span className="text-[#7dd3fc]">#</span> discovered candidates
      </h3>
      {toast && (
        <div
          role="status"
          className="border border-[#1f2329] bg-[#0e1115] text-xs font-mono text-[#d4d4d8] px-3 py-2 rounded"
        >
          {toast}
        </div>
      )}
      {error && <ErrorBanner message={error} />}
      {loading && (
        <p className="text-xs text-[#71717a] font-mono">
          loading discovered handles…
        </p>
      )}
      {data && !error && (
        <div className="overflow-x-auto border border-[#1f2329] rounded">
          <table className="w-full text-xs font-mono">
            <thead className="bg-[#0e1115] text-[#71717a] uppercase tracking-widest">
              <tr>
                <th className="text-left px-3 py-2">handle</th>
                <th className="text-right px-3 py-2">engagements</th>
                <th className="text-left px-3 py-2">seeds</th>
                <th className="text-left px-3 py-2">first seen</th>
                <th className="text-right px-3 py-2">actions</th>
              </tr>
            </thead>
            <tbody>
              {data.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-3 py-6 text-center text-[#52525b]"
                  >
                    no pending candidates
                  </td>
                </tr>
              ) : (
                data.map((h) => (
                  <tr
                    key={h.handle}
                    className="border-t border-[#1f2329] hover:bg-[#0e1115]"
                  >
                    <td className="px-3 py-2 text-[#d4d4d8]">@{h.handle}</td>
                    <td className="px-3 py-2 text-right text-[#a1a1aa]">
                      {h.seed_engagement_count}
                    </td>
                    <td className="px-3 py-2 text-[#71717a] max-w-xs truncate">
                      {h.seed_handles.join(", ")}
                    </td>
                    <td className="px-3 py-2 text-[#71717a]">
                      {new Date(h.first_seen_at).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => onAdd(h.handle)}
                          disabled={busy !== null}
                          className="px-2 py-1 text-[11px] uppercase tracking-widest border border-[#7cffb2] text-[#7cffb2] hover:bg-[#7cffb2]/10 disabled:opacity-50 rounded"
                        >
                          add
                        </button>
                        <button
                          type="button"
                          onClick={() => onIgnore(h.handle)}
                          disabled={busy !== null}
                          className="px-2 py-1 text-[11px] uppercase tracking-widest border border-[#52525b] text-[#71717a] hover:text-[#d4d4d8] disabled:opacity-50 rounded"
                        >
                          ignore
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function formatError(e: unknown): string {
  if (e instanceof AdminApiError) return `${e.status}: ${e.body}`;
  if (e instanceof Error) return e.message;
  return String(e);
}
