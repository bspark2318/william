# RSS Blog Aggregation — implementation plan

Replaces the X section in the `/api/devs/posts` feed with RSS-aggregated blog
posts from AI/engineering practitioners. X infra (table, source module) stays
dormant for easy re-enable if we later pay for Apify.

## Why

- Apify `apidojo/tweet-scraper` is rental-only (~$49/mo minimum).
- Bluesky has accounts but ~4 posts/day from the AI crowd — too thin.
- Target practitioners all blog, and long-form posts are 10× the signal of tweets.

## Decisions (locked)

- **Strategy**: replace X slot in published feed with blog content.
- **X infra**: stays in code, dormant. `publish_x` not called from `publish_dev_feed`.
- **Slot allocation**: `hn=3, github=2, blogs=3` (was `x_topics=3`).
- **UI label**: `BLOGS`.
- **Per-post synthesis**: LLM generates (a) 2-3 sentence summary, (b) 3-5 critical bullets.
- **Reading time estimate**: skipped.

## Blog list (15)

```yaml
blog_feeds:
  # Practitioners
  - https://simonwillison.net/atom.xml
  - https://www.eugeneyan.com/rss/
  - https://hamel.dev/index.xml
  - https://www.latent.space/feed
  - https://cameronrwolfe.substack.com/feed
  - https://karpathy.github.io/feed.xml
  - https://lilianweng.github.io/index.xml
  - https://jxnl.co/feed
  - https://sebastianraschka.com/blog/feed.xml
  - https://huyenchip.com/feed.xml
  # Agentic-coding focus (added on request)
  - https://www.anthropic.com/engineering/rss.xml
  - https://sourcegraph.com/blog/rss.xml
  - https://addyosmani.com/blog/feed/
  - https://aider.chat/blog/feed.xml
  # Lab announcements (technical enough to keep)
  - https://www.anthropic.com/news/rss.xml
```

OpenAI blog dropped — mostly PR/marketing, low ROI. All feed URLs must be
verified resolving before committing.

## Schema — extend `DevPost` (reuse)

New source value: `"blog"` (alongside `"hn"`, `"github"`).

**New nullable columns on `dev_posts`:**
- `author_name` (String) — e.g. "Simon Willison"
- `blog_name` (String) — e.g. "Simon Willison's Weblog"
- `summary` (Text) — LLM 2-3 sentence TL;DR

**Reused fields:**
- `bullets` (JSON list[str]) — LLM critical takeaways
- `topics` (JSON list[str]) — LLM-tagged topics
- `importance_score`, `rank_score`, `is_active`, `display_order`
- `title`, `url`, `published_at`

SQLite migration via existing `ensure_sqlite_columns()` pattern in `database.py`.

## New file: `backend/app/services/blog_source.py`

Mirror `hn_source.py` / `github_source.py` shape.

```python
def fetch_blog_entries(
    feeds: Iterable[str],
    *,
    lookback_days: int = 7,
    now: datetime | None = None,
) -> list[dict]: ...

def ingest_blogs(db: Session, *, ...) -> int: ...
```

- Uses `feedparser` (add to `requirements.txt`).
- 7-day lookback (blog cadence is weekly, not hourly).
- Dedup by URL against `dev_posts`.
- Normalized candidate dict shape:
  `{url, title, author_name, blog_name, excerpt, published_at, topics}`

## Ranker additions — `backend/app/services/devs_ranker.py`

- `rank_blog_post(entry)` → `{score: float, topics: list[str]}` (mirror `rank_hn_post`).
  Prompt tuned for long-form content (different signals than HN titles).
- `summarize_blog_post(title, body)` → `{summary: str, bullets: list[str]}`.
  Returns both pieces from a single LLM call. Body truncated to ~8k tokens.

## Pipeline wiring — `backend/app/services/devs_pipeline.py`

- Add `collect_blogs(db)` — mirrors `collect_hn`.
- Add `publish_blogs(db, *, start_order, now)` — mirrors `publish_hn`.
  Generates summary + bullets per finalist, writes to DevPost.
- `collect_dev_candidates` returns `{"hn", "github", "blogs", "x"}`.
- `publish_dev_feed`:
  - Stop calling `publish_x` (keep the function).
  - Call `publish_blogs` with `x_topics` slot count.
- Scheduler: no changes needed — `collect_dev_candidates` already wraps all three.

## Frontend — `/devs` page

New component: `frontend/components/devs/BlogPostCard.tsx`

**Render:**
```
[BLOGS accent marker]
Title (link → article)
  by Author Name · Blog Name · 2 days ago
  Summary (2-3 sentences, italic or muted)
  ▸ Bullet 1
  ▸ Bullet 2
  ▸ Bullet 3
```

**Changes:**
- `frontend/lib/devs/types.ts` — extend union with `BlogPost` variant.
- `frontend/app/devs/page.tsx` — add `blogs` section between HN and GitHub (or wherever reads best). Keep X section gated as-is.

## Tests

- `backend/tests/test_blog_source.py` — mocked feedparser fixtures.
- Extend `test_devs_ranker.py` with `rank_blog_post` + `summarize_blog_post`.
- Extend `test_devs_pipeline.py` with `collect_blogs` + `publish_blogs`.
- Frontend: `BlogPostCard` snapshot test in `__tests__/`.

## Task breakdown (for implementation)

1. Verify all 15 RSS feed URLs resolve, fix any 404s.
2. Add `feedparser` to `requirements.txt`. Install in venv.
3. Extend `DevPost` schema: `author_name`, `blog_name`, `summary`. Update `ensure_sqlite_columns`.
4. Write `blog_source.py` + unit tests.
5. Add `rank_blog_post` + `summarize_blog_post` in `devs_ranker.py` + tests.
6. Wire `collect_blogs` + `publish_blogs` into `devs_pipeline.py`. Stop calling `publish_x`. Update slot allocation.
7. Extend `devs_config.yaml` with `blog_feeds` section + `slot_allocation.blogs: 3`.
8. Live smoke test: collect + publish, verify 3 blog posts in `/api/devs/posts`.
9. Frontend: `BlogPostCard` component, types, page integration.
10. Frontend smoke test: browser check at `http://localhost:3000/devs`.

## Open items to decide during implementation

- Should `blog_feeds` be tiered like `x_handles` (tier_a/tier_b) for ranking weight? Or flat? Current lean: flat; ranker already scores by content.
- Retention: should old blog posts purge after 30 days like the rest, or longer since they're evergreen? Current lean: same 30d purge.
- Body fetch: some RSS feeds return summary only, not full content. Need a fallback to fetch the full article HTML for summarization. Lean: try `content:encoded` from feed first, fall back to GET on `url` + basic HTML-to-text stripping.

## Related (not in scope for this slice)

- GitHub issues from today's testing: #6 (apify-shared pin), #7 (SQLite bootstrap race), #8 (stale curated repos), #9 (Apify silent-0 on paywall). These are orthogonal — fix whenever.
- Eventually rename `CandidateXTweet` → `CandidateSocialPost` when a second social source lands.
