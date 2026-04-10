import { Story } from "@/lib/types";

interface StoryCardProps {
  story: Story;
}

export default function StoryCard({ story }: StoryCardProps) {
  const formattedDate = new Date(story.date + "T00:00:00").toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <a
      href={story.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group block"
    >
      <article className="py-4 transition-colors duration-200">
        <div className="flex gap-5">
          {/* Thumbnail */}
          {story.image_url && (
            <div className="hidden sm:block shrink-0 w-28 h-28 overflow-hidden bg-paper-alt">
              <img
                src={story.image_url}
                alt=""
                className="w-full h-full object-cover group-hover:opacity-80 transition-opacity duration-300"
              />
            </div>
          )}

          <div className="flex-1 min-w-0">
            {/* Source & date */}
            <div className="flex items-center gap-2 mb-1.5 text-xs text-ink-light">
              <span className="font-semibold uppercase tracking-wider text-accent">
                {story.source}
              </span>
              <span className="text-rule-dark">&middot;</span>
              <time dateTime={story.date}>{formattedDate}</time>
            </div>

            {/* Title */}
            <h3 className="font-headline text-lg md:text-xl font-bold text-ink leading-snug group-hover:text-accent transition-colors duration-200">
              {story.title}
            </h3>

            {/* Summary */}
            <p className="mt-1.5 text-sm text-ink-light leading-relaxed line-clamp-3">
              {story.summary}
            </p>

            {/* Tags */}
            {story.tags && story.tags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {story.tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 text-[10px] uppercase tracking-wider text-ink-light bg-paper-alt border border-rule"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </article>
    </a>
  );
}
