"use client";

import { useEffect, useState } from "react";
import { AdminApiError, Budget, getBudget } from "@/lib/devs/admin-api";
import ErrorBanner from "./ErrorBanner";

const REFRESH_MS = 60_000;

export default function BudgetPanel() {
  const [data, setData] = useState<Budget | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const b = await getBudget();
        if (!cancelled) {
          setData(b);
          setError(null);
          setLastUpdated(new Date().toISOString());
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof AdminApiError
              ? `${e.status}: ${e.body}`
              : e instanceof Error
                ? e.message
                : String(e),
          );
        }
      }
    }

    load();
    const interval = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const paused = data?.will_pause_at !== null && data?.will_pause_at !== undefined;

  return (
    <div className="space-y-4">
      {error && <ErrorBanner message={error} />}
      {!data && !error && (
        <p className="text-xs text-[#71717a] font-mono">loading budget…</p>
      )}

      {data && (
        <>
          <div className="border border-[#1f2329] rounded bg-[#0e1115] p-6">
            <div className="text-xs uppercase tracking-widest text-[#71717a] mb-2">
              apify tweet budget (30d rolling)
            </div>
            <div
              className={`font-mono text-5xl md:text-6xl font-bold ${colorFor(data.pct_used)}`}
            >
              {data.pct_used.toFixed(1)}%
            </div>
            <div className="mt-3 h-2 rounded bg-[#1f2329] overflow-hidden">
              <div
                role="progressbar"
                aria-valuenow={data.pct_used}
                aria-valuemin={0}
                aria-valuemax={100}
                className={`h-full ${bgFor(data.pct_used)}`}
                style={{ width: `${Math.min(100, data.pct_used)}%` }}
              />
            </div>
          </div>

          <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <Stat label="used" value={data.tweets_used_30d.toLocaleString()} />
            <Stat label="cap" value={data.tweets_cap.toLocaleString()} />
            <Stat
              label="remaining"
              value={data.remaining.toLocaleString()}
            />
          </dl>

          {paused && (
            <div
              role="alert"
              className="border border-red-500/50 bg-red-500/10 text-red-300 text-xs font-mono px-3 py-2 rounded"
            >
              x collection paused — cap reached
              {data.will_pause_at
                ? ` at ${new Date(data.will_pause_at).toLocaleString()}`
                : ""}
            </div>
          )}

          <p className="text-[11px] text-[#52525b] font-mono">
            auto-refreshing every 60s
            {lastUpdated && (
              <>
                {" · last "}
                {new Date(lastUpdated).toLocaleTimeString()}
              </>
            )}
          </p>
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-[#1f2329] rounded bg-[#0e1115] p-4">
      <dt className="text-[#71717a] uppercase tracking-widest text-[11px]">
        {label}
      </dt>
      <dd className="text-[#d4d4d8] text-xl mt-1">{value}</dd>
    </div>
  );
}

function colorFor(pct: number): string {
  if (pct >= 90) return "text-red-400";
  if (pct >= 70) return "text-amber-300";
  return "text-[#7cffb2]";
}

function bgFor(pct: number): string {
  if (pct >= 90) return "bg-red-400";
  if (pct >= 70) return "bg-amber-300";
  return "bg-[#7cffb2]";
}
