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
      featured_videos: [makeVideo({ id: 1, title: "Solo Video" })],
    });

    render(<NewsletterLayout issue={issue} />);

    expect(screen.getAllByRole("heading", { name: /The Context Window/i })[0]).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Weekly Headline" })).toBeInTheDocument();
    expect(screen.getByText("This Week's Stories")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Alpha" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Beta" })).toBeInTheDocument();
  });

  it("renders a single sidebar video from featured_videos", () => {
    const v = makeVideo({ id: 9, title: "Only Clip", video_url: "https://example.com/v" });
    const issue = makeIssue({
      stories: [],
      featured_videos: [v],
    });

    render(<NewsletterLayout issue={issue} />);

    const link = screen.getByRole("link", { name: /Only Clip/i });
    expect(link).toHaveAttribute("href", "https://example.com/v");
    expect(screen.getByText("Featured Videos")).toBeInTheDocument();
  });

  it("renders featured_videos with a label on the first item", () => {
    const issue = makeIssue({
      stories: [],
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

  it("shows at most three sidebar videos", () => {
    const issue = makeIssue({
      stories: [],
      featured_videos: [
        makeVideo({ id: 1, title: "V1" }),
        makeVideo({ id: 2, title: "V2" }),
        makeVideo({ id: 3, title: "V3" }),
        makeVideo({ id: 4, title: "V4 Hidden" }),
      ],
    });

    const { container } = render(<NewsletterLayout issue={issue} />);

    const aside = container.querySelector("aside");
    expect(aside).toBeTruthy();
    expect(within(aside as HTMLElement).getAllByRole("link")).toHaveLength(3);
    expect(screen.queryByRole("heading", { name: "V4 Hidden" })).not.toBeInTheDocument();
  });

  it("renders footer branding", () => {
    const issue = makeIssue({ stories: [] });
    render(<NewsletterLayout issue={issue} />);

    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("The Context Window")).toBeInTheDocument();
    expect(
      within(footer).getByText(/Published weekly for researchers/i),
    ).toBeInTheDocument();
  });
});
