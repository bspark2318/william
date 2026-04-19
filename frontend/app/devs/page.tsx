import type { Metadata } from "next";
import DevHeader from "@/components/devs/DevHeader";
import XTopicTabs from "@/components/devs/XTopicTabs";
import HNPostCard from "@/components/devs/HNPostCard";
import GitHubRotator from "@/components/devs/GitHubRotator";
import { getDevPosts } from "@/lib/devs/api";
import { MOCK_DEV_POSTS } from "@/lib/devs/mock-data";
import {
  DevPost,
  GitHubPost,
  HNPost,
  XTopicDigest,
} from "@/lib/devs/types";

export const metadata: Metadata = {
  title: "The Context Window — For Developers",
  description:
    "Signals to level up as an AI-era engineer — curated posts from X, Hacker News, and GitHub.",
};

async function fetchPosts(): Promise<DevPost[]> {
  try {
    const posts = await getDevPosts();
    if (posts.length === 0) return MOCK_DEV_POSTS;
    return posts;
  } catch {
    return MOCK_DEV_POSTS;
  }
}

function bySource(posts: DevPost[]) {
  const byDisplay = [...posts].sort((a, b) => a.display_order - b.display_order);
  return {
    x: byDisplay.filter((p): p is XTopicDigest => p.source === "x"),
    hn: byDisplay.filter((p): p is HNPost => p.source === "hn"),
    github: byDisplay.filter((p): p is GitHubPost => p.source === "github"),
  };
}

function SectionLabel({
  children,
  accent = "#7cffb2",
  size = "sm",
}: {
  children: React.ReactNode;
  accent?: string;
  size?: "sm" | "lg";
}) {
  const cls =
    size === "lg"
      ? "text-sm md:text-base font-semibold"
      : "text-xs";
  return (
    <div
      className={`flex items-center gap-2 mb-4 ${cls} text-[#d4d4d8] uppercase tracking-widest`}
    >
      <span style={{ color: accent }}>#</span>
      <span>{children}</span>
      <span className="flex-1 h-px bg-[#1f2329] ml-2" />
    </div>
  );
}

export default async function DevsPage() {
  const posts = await fetchPosts();
  const { x, hn, github } = bySource(posts);

  return (
    <div className="max-w-3xl mx-auto px-4 md:px-8 py-10 md:py-16">
      <DevHeader />

      <div className="space-y-10">
        {x.length > 0 && (
          <section>
            <SectionLabel accent="#7dd3fc" size="lg">
              x
            </SectionLabel>
            <XTopicTabs topics={x} />
          </section>
        )}

        {hn.length > 0 && (
          <section>
            <SectionLabel accent="#fbbf24">hn</SectionLabel>
            <div className="space-y-3">
              {hn.map((post) => (
                <HNPostCard key={post.id} post={post} />
              ))}
            </div>
          </section>
        )}

        {github.length > 0 && (
          <section>
            <SectionLabel accent="#7cffb2">github</SectionLabel>
            <GitHubRotator posts={github} />
          </section>
        )}

        {posts.length === 0 && (
          <p className="text-sm text-[#a1a1aa]">
            <span className="text-[#7cffb2]">$</span> no signals right now &mdash; check back soon.
          </p>
        )}
      </div>

      <footer className="mt-16 pt-6 border-t border-[#1f2329] text-xs text-[#52525b]">
        <div className="flex flex-wrap gap-x-4 gap-y-1">
          <span>
            <span className="text-[#71717a]">&copy;</span>{" "}
            {new Date().getFullYear()} The Context Window
          </span>
          <span>&middot;</span>
          <span>built for developers</span>
        </div>
      </footer>
    </div>
  );
}
