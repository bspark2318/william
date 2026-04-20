"use client";

import { useState } from "react";
import {
  AdminApiError,
  CollectResponse,
  PublishResponse,
  runCollect,
  runPublish,
} from "@/lib/devs/admin-api";
import ErrorBanner from "./ErrorBanner";

type Result =
  | { kind: "collect"; at: string; data: CollectResponse }
  | { kind: "publish"; at: string; data: PublishResponse };

export default function PipelineControls() {
  const [busy, setBusy] = useState<"collect" | "publish" | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(true);

  async function onCollect() {
    setBusy("collect");
    setError(null);
    try {
      const data = await runCollect();
      setResult({ kind: "collect", at: new Date().toISOString(), data });
    } catch (e) {
      setError(
        e instanceof AdminApiError
          ? `${e.status}: ${e.body}`
          : e instanceof Error
            ? e.message
            : String(e),
      );
    } finally {
      setBusy(null);
    }
  }

  async function onPublish() {
    setBusy("publish");
    setError(null);
    try {
      const data = await runPublish();
      setResult({ kind: "publish", at: new Date().toISOString(), data });
    } catch (e) {
      setError(
        e instanceof AdminApiError
          ? `${e.status}: ${e.body}`
          : e instanceof Error
            ? e.message
            : String(e),
      );
    } finally {
      setBusy(null);
    }
  }

  const disabled = busy !== null;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          type="button"
          onClick={onCollect}
          disabled={disabled}
          aria-busy={busy === "collect"}
          className="flex-1 px-4 py-3 text-sm uppercase tracking-widest font-semibold border border-[#7cffb2] text-[#7cffb2] hover:bg-[#7cffb2]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded"
        >
          {busy === "collect" ? "running…" : "run collect"}
        </button>
        <button
          type="button"
          onClick={onPublish}
          disabled={disabled}
          aria-busy={busy === "publish"}
          className="flex-1 px-4 py-3 text-sm uppercase tracking-widest font-semibold border border-[#7dd3fc] text-[#7dd3fc] hover:bg-[#7dd3fc]/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors rounded"
        >
          {busy === "publish" ? "running…" : "run publish"}
        </button>
      </div>

      {error && <ErrorBanner message={error} />}

      {result && (
        <div className="border border-[#1f2329] rounded bg-[#0e1115]">
          <button
            type="button"
            onClick={() => setDetailsOpen((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-3 text-xs uppercase tracking-widest text-[#a1a1aa] hover:text-[#d4d4d8]"
            aria-expanded={detailsOpen}
          >
            <span>
              <span className="text-[#7cffb2]">$</span> last {result.kind}{" "}
              response
            </span>
            <span className="text-[#52525b]">{detailsOpen ? "−" : "+"}</span>
          </button>
          {detailsOpen && (
            <div className="px-4 pb-4 text-xs font-mono text-[#d4d4d8]">
              <div className="text-[#52525b] mb-2">
                at {new Date(result.at).toLocaleTimeString()}
              </div>
              <pre className="whitespace-pre-wrap break-words bg-[#0b0d10] p-3 rounded border border-[#1f2329] overflow-x-auto">
                {JSON.stringify(result.data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
