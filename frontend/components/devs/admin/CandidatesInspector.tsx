"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AdminApiError,
  Candidate,
  getCandidates,
} from "@/lib/devs/admin-api";
import ErrorBanner from "./ErrorBanner";

type SourceFilter = "all" | "x" | "hn" | "github";

export default function CandidatesInspector() {
  const [data, setData] = useState<Candidate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [activeOnly, setActiveOnly] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const rows = await getCandidates();
        if (!cancelled) setData(rows);
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
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.filter((c) => {
      if (sourceFilter !== "all" && c.source !== sourceFilter) return false;
      if (activeOnly && !c.is_active) return false;
      return true;
    });
  }, [data, sourceFilter, activeOnly]);

  function toggle(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs uppercase tracking-widest text-[#71717a] mr-2">
          source:
        </span>
        {(["all", "x", "hn", "github"] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setSourceFilter(s)}
            aria-pressed={sourceFilter === s}
            className={`px-3 py-1 text-xs uppercase tracking-widest rounded border transition-colors ${
              sourceFilter === s
                ? "border-[#7cffb2] text-[#7cffb2] bg-[#7cffb2]/10"
                : "border-[#1f2329] text-[#71717a] hover:text-[#d4d4d8]"
            }`}
          >
            {s}
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2 text-xs uppercase tracking-widest text-[#71717a] cursor-pointer">
          <input
            type="checkbox"
            checked={activeOnly}
            onChange={(e) => setActiveOnly(e.target.checked)}
            className="accent-[#7cffb2]"
          />
          active only
        </label>
      </div>

      {error && <ErrorBanner message={error} />}
      {loading && (
        <p className="text-xs text-[#71717a] font-mono">loading candidates…</p>
      )}

      {data && !error && (
        <div className="overflow-x-auto border border-[#1f2329] rounded">
          <table className="w-full text-xs font-mono">
            <thead className="bg-[#0e1115] text-[#71717a] uppercase tracking-widest">
              <tr>
                <th className="text-left px-3 py-2 w-8" />
                <th className="text-left px-3 py-2">src</th>
                <th className="text-left px-3 py-2">title / text</th>
                <th className="text-right px-3 py-2">imp</th>
                <th className="text-right px-3 py-2">rank</th>
                <th className="text-center px-3 py-2">active</th>
                <th className="text-right px-3 py-2">ord</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-3 py-6 text-center text-[#52525b]"
                  >
                    no candidates match filters
                  </td>
                </tr>
              ) : (
                filtered.map((c) => {
                  const isOpen = expanded.has(c.id);
                  const label = c.title ?? c.text ?? c.url;
                  return (
                    <FragmentRow
                      key={c.id}
                      candidate={c}
                      label={label}
                      isOpen={isOpen}
                      onToggle={() => toggle(c.id)}
                    />
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function FragmentRow({
  candidate,
  label,
  isOpen,
  onToggle,
}: {
  candidate: Candidate;
  label: string;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const truncated = label.length > 120 ? label.slice(0, 120) + "…" : label;
  return (
    <>
      <tr
        className={`border-t border-[#1f2329] ${isOpen ? "bg-[#0f1620]" : "hover:bg-[#0e1115]"}`}
      >
        <td className="px-3 py-2 text-[#52525b]">
          <button
            type="button"
            onClick={onToggle}
            aria-expanded={isOpen}
            aria-label={isOpen ? "collapse row" : "expand row"}
            className="hover:text-[#d4d4d8]"
          >
            {isOpen ? "▾" : "▸"}
          </button>
        </td>
        <td className="px-3 py-2">
          <SourceTag source={candidate.source} />
        </td>
        <td className="px-3 py-2 text-[#d4d4d8]">{truncated}</td>
        <td className="px-3 py-2 text-right text-[#a1a1aa]">
          {formatScore(candidate.importance_score)}
        </td>
        <td className="px-3 py-2 text-right text-[#a1a1aa]">
          {formatScore(candidate.rank_score)}
        </td>
        <td className="px-3 py-2 text-center">
          {candidate.is_active ? (
            <span className="text-[#7cffb2]">✓</span>
          ) : (
            <span className="text-[#52525b]">−</span>
          )}
        </td>
        <td className="px-3 py-2 text-right text-[#a1a1aa]">
          {candidate.is_active ? (candidate.display_order ?? "—") : "—"}
        </td>
      </tr>
      {isOpen && (
        <tr className="bg-[#0b0d10] border-t border-[#1f2329]">
          <td colSpan={7} className="px-6 py-4">
            <div className="space-y-2">
              <div className="text-[11px] text-[#52525b] uppercase tracking-widest">
                id {candidate.id} · collected{" "}
                {new Date(candidate.collected_at).toLocaleString()}
              </div>
              <a
                href={candidate.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block text-[11px] text-[#7dd3fc] hover:underline break-all"
              >
                {candidate.url}
              </a>
              <div className="text-[11px] text-[#71717a] uppercase tracking-widest mt-2">
                rank_features
              </div>
              <pre className="bg-[#0e1115] border border-[#1f2329] rounded p-3 text-[11px] text-[#d4d4d8] overflow-x-auto">
                {candidate.rank_features
                  ? JSON.stringify(candidate.rank_features, null, 2)
                  : "null"}
              </pre>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function SourceTag({ source }: { source: "x" | "hn" | "github" }) {
  const color =
    source === "x"
      ? "text-[#7dd3fc]"
      : source === "hn"
        ? "text-[#fbbf24]"
        : "text-[#7cffb2]";
  return (
    <span className={`${color} uppercase tracking-widest`}>{source}</span>
  );
}

function formatScore(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return n.toFixed(2);
}
