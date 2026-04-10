import { Issue } from "@/lib/types";
import Masthead from "./Masthead";
import StoryFeed from "./StoryFeed";
import VideoPreview from "./VideoPreview";

interface NewsletterLayoutProps {
  issue: Issue;
  allIssueIds?: { id: number; week_of: string }[];
}

export default function NewsletterLayout({ issue, allIssueIds }: NewsletterLayoutProps) {
  return (
    <div className="max-w-6xl mx-auto px-4 md:px-8 pb-16">
      <Masthead
        weekOf={issue.week_of}
        title={issue.title}
        issueNumber={issue.edition}
      />

      {/* Two-column newspaper layout */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_300px] gap-8 mt-6">
        {/* Stories — main column */}
        <main className="min-w-0">
          <div className="divider-label">
            <span className="text-[11px] text-ink-light uppercase tracking-[0.2em] font-body whitespace-nowrap font-semibold">
              This Week&apos;s Stories
            </span>
          </div>
          <StoryFeed stories={issue.stories} />
        </main>

        {/* Sidebar — video + info */}
        <aside className="md:sticky md:top-6 md:self-start space-y-6">
          {(() => {
            const raw =
              issue.featured_videos ?? (issue.featured_video ? [issue.featured_video] : []);
            const videos = raw.slice(0, 3);
            return videos.map((video, i) => (
              <VideoPreview key={video.id} video={video} showLabel={i === 0} />
            ));
          })()}
        </aside>
      </div>

      {/* Footer */}
      <footer className="mt-12 pt-4 border-t-2 border-ink">
        <div className="max-w-md mx-auto text-center">
          <p className="font-masthead text-lg text-ink font-bold">
            The Context Window
          </p>
          <p className="text-xs text-ink-light mt-1 leading-relaxed">
            Published weekly for researchers, engineers, and leaders navigating
            the frontier of artificial intelligence.
          </p>
          <div className="mt-3 border-t border-rule pt-3">
            <p className="text-[10px] text-ink-light uppercase tracking-widest">
              &ldquo;All the AI news that&apos;s fit to print&rdquo;
            </p>
          </div>
          <p className="text-xs text-ink-light mt-3">
            &copy; {new Date().getFullYear()} The Context Window
          </p>
        </div>
      </footer>
    </div>
  );
}
