"use client";

import { useState } from "react";
import { XTopicDigest } from "@/lib/devs/types";

export default function XTopicTabs({ topics }: { topics: XTopicDigest[] }) {
  const [active, setActive] = useState(0);

  if (topics.length === 0) return null;

  const safe = active % topics.length;
  const current = topics[safe];

  return (
    <div>
      {topics.length > 1 && (
        <div
          role="tablist"
          aria-label="X topics"
          className="flex flex-wrap gap-2 mb-4 border-b border-[#1f2329]"
        >
          {topics.map((t, i) => {
            const selected = i === safe;
            return (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={selected}
                aria-controls={`x-topic-panel-${t.id}`}
                id={`x-topic-tab-${t.id}`}
                onClick={() => setActive(i)}
                className={`px-3 py-2 text-xs uppercase tracking-widest transition-colors -mb-px border-b-2 ${
                  selected
                    ? "text-[#7dd3fc] border-[#7dd3fc]"
                    : "text-[#71717a] border-transparent hover:text-[#a1a1aa]"
                }`}
              >
                <span className="text-[#52525b] mr-1">#</span>
                {t.topic}
              </button>
            );
          })}
        </div>
      )}

      <div
        key={current.id}
        id={`x-topic-panel-${current.id}`}
        role="tabpanel"
        aria-labelledby={`x-topic-tab-${current.id}`}
        className="animate-slide-in rounded-md border border-[#1f2329] border-l-2 border-l-[#7dd3fc] bg-gradient-to-br from-[#0f1620] to-[#0e1115] p-5 md:p-6"
      >
        <ul className="space-y-4">
          {current.bullets.map((b, i) => (
            <li key={i} className="flex gap-3">
              <span aria-hidden className="text-[#7dd3fc] mt-1">•</span>
              <div className="flex-1 space-y-2">
                <p className="text-sm md:text-base text-[#e4e4e7] leading-relaxed">
                  {b.text}
                </p>
                {b.sources.length > 0 && (
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]">
                    {b.sources.map((s) => (
                      <a
                        key={s.url}
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#7dd3fc] hover:underline"
                      >
                        @{s.author_handle}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
