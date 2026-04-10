import { Story, FeaturedVideo, Issue } from "@/lib/types";

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
    featured_video: null,
    ...overrides,
  };
}
