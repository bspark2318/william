import { Story, FeaturedVideo, Issue } from "@/lib/types";
import { XTopicDigest, HNPost, GitHubPost } from "@/lib/devs/types";

export function makeStory(overrides: Partial<Story> = {}): Story {
  return {
    id: 1,
    title: "Test AI Story",
    summary: "A brief summary of the story.",
    source: "TestSource",
    url: "https://example.com/story",
    date: "2026-04-07",
    display_order: 1,
    ...overrides,
  };
}

export function makeVideo(overrides: Partial<FeaturedVideo> = {}): FeaturedVideo {
  return {
    id: 1,
    title: "Test Video Title",
    video_url: "https://youtube.com/watch?v=abc",
    thumbnail_url: "https://img.youtube.com/vi/abc/0.jpg",
    description: "A test video description.",
    ...overrides,
  };
}

export function makeIssue(overrides: Partial<Issue> = {}): Issue {
  return {
    id: 1,
    week_of: "2026-04-07",
    title: "Test Issue Title",
    edition: 1,
    stories: [makeStory()],
    featured_videos: [],
    ...overrides,
  };
}

export function makeXTopicDigest(
  overrides: Partial<XTopicDigest> = {},
): XTopicDigest {
  return {
    id: 1,
    source: "x",
    display_order: 1,
    topic: "evals",
    bullets: [
      {
        text: "A sample bullet on evals.",
        sources: [
          { url: "https://x.com/testuser/status/1", author_handle: "testuser" },
        ],
      },
    ],
    ...overrides,
  };
}

export function makeHNPost(overrides: Partial<HNPost> = {}): HNPost {
  return {
    id: 2,
    source: "hn",
    url: "https://example.com/article",
    hn_url: "https://news.ycombinator.com/item?id=1",
    published_at: "2026-04-18",
    display_order: 2,
    title: "A practical essay on LLM workflows",
    points: 250,
    comments: 80,
    ...overrides,
  };
}

export function makeGitHubPost(overrides: Partial<GitHubPost> = {}): GitHubPost {
  return {
    id: 3,
    source: "github",
    url: "https://github.com/test/repo",
    published_at: "2026-04-18",
    display_order: 3,
    repo: "test/repo",
    title: "v1.2.0",
    version: "v1.2.0",
    stars: 1500,
    stars_velocity_7d: 120,
    ...overrides,
  };
}
