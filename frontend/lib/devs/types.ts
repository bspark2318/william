export interface BasePost {
  id: number;
  rank_score?: number;
  display_order: number;
}

export interface HNPost extends BasePost {
  source: "hn";
  url: string;
  published_at: string;
  title: string;
  hn_url: string;
  points: number;
  comments: number;
  /** LLM-generated bullet summary of what the thread is actually discussing. */
  bullets?: string[];
  /** Optional standout comment — shown when bullets absent, or as supplementary quote. */
  top_comment_excerpt?: string;
  topics?: string[];
}

export interface GitHubPost extends BasePost {
  source: "github";
  url: string;
  published_at: string;
  repo: string;
  title: string;
  version?: string;
  /** LLM-extracted notable changes (preferred). */
  release_bullets?: string[];
  /** Fallback blob used when bullets aren't available. */
  release_notes_excerpt?: string;
  /** LLM one-liner on why a senior engineer should care. */
  why_it_matters?: string;
  has_breaking_changes?: boolean;
  stars?: number;
  stars_velocity_7d?: number;
  topics?: string[];
}

export type DevPost = HNPost | GitHubPost;
