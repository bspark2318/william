import { HNPost } from "@/lib/devs/types";

export default function HNPostCard({ post }: { post: HNPost }) {
  return (
    <article className="relative border border-[#1f2329] rounded-lg bg-gradient-to-br from-[#1a1410] to-[#0e1115] p-5 md:p-6 border-l-2 border-l-[#fbbf24] shadow-lg shadow-black/20">
      <a
        href={post.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block text-base md:text-lg font-semibold text-white hover:text-[#fbbf24] transition-colors leading-snug"
      >
        {post.title}
      </a>

      <div className="mt-3 flex items-center gap-4 text-xs text-[#a1a1aa]">
        <span className="font-medium">
          <span className="text-[#fbbf24]">&#x25b2;</span> {post.points}
        </span>
        <a
          href={post.hn_url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-[#d4d4d8]"
        >
          {post.comments} comments
        </a>
        <span className="ml-auto text-[#52525b]">{post.published_at}</span>
      </div>

      {post.bullets && post.bullets.length > 0 ? (
        <ul className="mt-4 space-y-2 text-sm text-[#d4d4d8] leading-relaxed">
          {post.bullets.map((b, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-[#fbbf24] select-none">&bull;</span>
              <span>{b}</span>
            </li>
          ))}
        </ul>
      ) : post.top_comment_excerpt ? (
        <blockquote className="mt-4 border-l-2 border-[#fbbf24]/40 pl-4 text-sm text-[#d4d4d8] italic leading-relaxed">
          {post.top_comment_excerpt}
        </blockquote>
      ) : null}
    </article>
  );
}
