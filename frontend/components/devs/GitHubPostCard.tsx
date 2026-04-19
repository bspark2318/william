import { GitHubPost } from "@/lib/devs/types";

export default function GitHubPostCard({ post }: { post: GitHubPost }) {
  return (
    <article className="relative border border-[#1f2329] rounded-lg bg-gradient-to-br from-[#0e1914] to-[#0e1115] p-5 md:p-6 border-l-2 border-l-[#7cffb2] shadow-lg shadow-black/20">
      <header className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm">
        <a
          href={post.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-base md:text-lg text-[#7cffb2] font-semibold hover:underline"
        >
          {post.repo}
        </a>
        {post.version && (
          <span className="text-[#a1a1aa]">
            <span className="text-[#52525b]">@</span>
            {post.version}
          </span>
        )}
        {post.has_breaking_changes && (
          <span className="px-1.5 py-0.5 text-[10px] uppercase tracking-widest rounded border border-[#fbbf24]/40 text-[#fbbf24] bg-[#fbbf24]/10">
            Breaking
          </span>
        )}
        <span className="ml-auto text-xs text-[#52525b]">{post.published_at}</span>
      </header>

      <h3 className="mt-2 text-base md:text-lg font-semibold text-white">
        {post.title}
      </h3>

      {post.why_it_matters && (
        <p className="mt-3 text-sm italic text-[#a7f3d0] leading-relaxed border-l-2 border-[#7cffb2]/30 pl-3">
          {post.why_it_matters}
        </p>
      )}

      {post.release_bullets && post.release_bullets.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {post.release_bullets.map((b, i) => (
            <li
              key={i}
              className="flex gap-2 text-sm text-[#d4d4d8] leading-relaxed"
            >
              <span aria-hidden className="text-[#7cffb2] mt-0.5">&rsaquo;</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      ) : (
        post.release_notes_excerpt && (
          <p className="mt-3 text-sm text-[#d4d4d8] leading-relaxed">
            {post.release_notes_excerpt}
          </p>
        )
      )}

      <footer className="mt-4 flex items-center gap-5 text-xs text-[#a1a1aa]">
        {post.stars != null && (
          <span className="font-medium">
            <span className="text-[#fbbf24]">&#x2605;</span> {post.stars.toLocaleString()}
          </span>
        )}
        {post.stars_velocity_7d != null && (
          <span className="text-[#7cffb2] font-medium">
            +{post.stars_velocity_7d.toLocaleString()} / 7d
          </span>
        )}
      </footer>
    </article>
  );
}
