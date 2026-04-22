"use client";

import { useState } from "react";
import PipelineControls from "./PipelineControls";
import CandidatesInspector from "./CandidatesInspector";

const TABS = [
  { id: "pipeline", label: "pipeline" },
  { id: "candidates", label: "candidates" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function AdminConsole() {
  const [active, setActive] = useState<TabId>("pipeline");

  return (
    <div className="space-y-6">
      <div
        role="tablist"
        aria-label="admin panels"
        className="flex flex-wrap gap-1 border-b border-[#1f2329]"
      >
        {TABS.map((t) => {
          const selected = active === t.id;
          return (
            <button
              key={t.id}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls={`admin-panel-${t.id}`}
              id={`admin-tab-${t.id}`}
              onClick={() => setActive(t.id)}
              className={`px-4 py-2 text-xs uppercase tracking-widest transition-colors -mb-px border-b-2 ${
                selected
                  ? "text-[#7cffb2] border-[#7cffb2]"
                  : "text-[#71717a] border-transparent hover:text-[#d4d4d8]"
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`admin-panel-${active}`}
        aria-labelledby={`admin-tab-${active}`}
      >
        {active === "pipeline" && <PipelineControls />}
        {active === "candidates" && <CandidatesInspector />}
      </div>
    </div>
  );
}
