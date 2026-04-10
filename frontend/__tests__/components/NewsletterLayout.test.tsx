import { render, screen, within } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import NewsletterLayout from "@/components/NewsletterLayout";
import { makeIssue, makeStory, makeVideo } from "../helpers";

describe("NewsletterLayout", () => {
  it("renders masthead, issue title, and story content", () => {
    const issue = makeIssue({
      title: "Weekly Headline",
      stories: [
        makeStory({ id: 1, title: "Alpha", display_order: 1 }),
        makeStory({ id: 2, title: "Beta", display_order: 2 }),
      ],
      featured_video: makeVideo({ id: 1, title: "Solo Video" }),
    });

    render(<NewsletterLayout issue={issue} />);

    expect(screen.getAllByRole("heading", { name: /The AI Prophet/i })[0]).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Weekly Headline" })).toBeInTheDocument();
    expect(screen.getByText("This Week's Stories")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Beta" })).toBeInTheDocument();
  });

  it("uses featured_video as a single sidebar video when featured_videos is absent", () => {
    const v = makeVideo({ id: 9, title: "Only Clip", video_url: "https://example.com/v" });
    const issue = makeIssue({
      stories: [],
      featured_video: v,
    });

    render(<NewsletterLayout issue={issue} />);

    const link = screen.getByRole("link", { name: /Only Clip/i });
    expect(link).toHaveAttribute("href", "https://example.com/v");
    expect(screen.getByText("Featured Videos")).toBeInTheDocument();
  });

  it("renders featured_videos with a label on the first item", () => {
    const issue = makeIssue({
      stories: [],
      featured_video: null,
      featured_videos: [
        makeVideo({ id: 1, title: "First Vid" }),
        makeVideo({ id: 2, title: "Second Vid" }),
      ],
    });

    render(<NewsletterLayout issue={issue} />);

    expect(screen.getByText("Featured Videos")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "First Vid" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Second Vid" })).toBeInTheDocument();
  });

  it("renders footer branding", () => {
    const issue = makeIssue({ stories: [] });
    render(<NewsletterLayout issue={issue} />);

    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("The AI Prophet")).toBeInTheDocument();
    expect(
      within(footer).getByText(/Published weekly for researchers/i),
    ).toBeInTheDocument();
  });
});
