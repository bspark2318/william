"use client";

import { useEffect, useState } from "react";
import { GitHubPost } from "@/lib/devs/types";
import GitHubPostCard from "./GitHubPostCard";

const ROTATE_MS = 3500;

export default function GitHubRotator({ posts }: { posts: GitHubPost[] }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    if (paused || reducedMotion || posts.length <= 1) return;
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % posts.length);
    }, ROTATE_MS);
    return () => clearInterval(id);
  }, [paused, reducedMotion, posts.length]);

  if (posts.length === 0) return null;

  const safeIndex = index % posts.length;
  const current = posts[safeIndex];

  return (
    <div
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={() => setPaused(false)}
    >
      <div className="overflow-hidden">
        <div key={current.id} className="animate-slide-in">
          <GitHubPostCard post={current} />
        </div>
      </div>

      {posts.length > 1 && (
        <div className="mt-3 flex items-center justify-center gap-3">
          <div
            className="flex items-center gap-2"
            role="tablist"
            aria-label="GitHub items"
          >
            {posts.map((post, i) => (
              <button
                key={post.id}
                type="button"
                role="tab"
                aria-selected={i === safeIndex}
                aria-label={`Show item ${i + 1} of ${posts.length}`}
                onClick={() => setIndex(i)}
                className={`h-2 rounded-full transition-all ${
                  i === safeIndex
                    ? "w-8 bg-[#7cffb2]"
                    : "w-2 bg-[#3f3f46] hover:bg-[#52525b]"
                }`}
              />
            ))}
          </div>
          <span className="text-[10px] text-[#52525b] uppercase tracking-widest tabular-nums">
            {safeIndex + 1}/{posts.length}
            {paused && <span className="ml-2 text-[#fbbf24]">paused</span>}
          </span>
        </div>
      )}
    </div>
  );
}
