"use client";

import { useRouter } from "next/navigation";

interface WeekNavProps {
  prevIssueId?: number;
  nextIssueId?: number;
  prevLabel?: string;
  nextLabel?: string;
}

export default function WeekNav({ prevIssueId, nextIssueId, prevLabel, nextLabel }: WeekNavProps) {
  const router = useRouter();

  return (
    <nav className="flex items-center justify-between py-2.5 border-b border-rule">
      {prevIssueId != null ? (
        <button
          onClick={() => router.push(`/?issue=${prevIssueId}`)}
          className="flex items-center gap-2 text-sm text-ink-light hover:text-accent transition-colors cursor-pointer"
        >
          <span>&larr;</span>
          <span className="font-body">
            Previous {prevLabel && <span className="hidden sm:inline">({prevLabel})</span>}
          </span>
        </button>
      ) : (
        <div />
      )}

      <span className="text-[11px] text-ink-light uppercase tracking-[0.15em] font-body font-semibold">
        Weekly Edition
      </span>

      {nextIssueId != null ? (
        <button
          onClick={() => router.push(`/?issue=${nextIssueId}`)}
          className="flex items-center gap-2 text-sm text-ink-light hover:text-accent transition-colors cursor-pointer"
        >
          <span className="font-body">
            Next {nextLabel && <span className="hidden sm:inline">({nextLabel})</span>}
          </span>
          <span>&rarr;</span>
        </button>
      ) : (
        <div />
      )}
    </nav>
  );
}
