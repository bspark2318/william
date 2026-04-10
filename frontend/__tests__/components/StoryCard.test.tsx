import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StoryCard from "@/components/StoryCard";
import { makeStory } from "../helpers";

describe("StoryCard", () => {
  it("renders title, bullets, and source", () => {
    const story = makeStory({
      title: "GPT-5 Released",
      summary: "ignored when bullets set",
      bullet_points: ["Ships multimodal.", "Higher math scores.", "Same API pricing."],
      source: "The Verge",
    });
    render(<StoryCard story={story} />);

    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent("GPT-5 Released");
    expect(screen.getByText("Ships multimodal.")).toBeInTheDocument();
    expect(screen.getByText("Higher math scores.")).toBeInTheDocument();
    expect(screen.queryByText("ignored when bullets set")).not.toBeInTheDocument();
    expect(screen.getByText("The Verge")).toBeInTheDocument();
  });

  it("falls back to summary as a single bullet when bullet_points absent", () => {
    const story = makeStory({
      summary: "One line only.",
      bullet_points: undefined,
    });
    render(<StoryCard story={story} />);
    expect(screen.getByText("One line only.")).toBeInTheDocument();
  });

  it("links to the story URL in a new tab", () => {
    const story = makeStory({ url: "https://example.com/ai-news" });
    render(<StoryCard story={story} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://example.com/ai-news");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders tags when provided", () => {
    const story = makeStory({ tags: ["LLM", "Open Source"] });
    render(<StoryCard story={story} />);

    expect(screen.getByText("LLM")).toBeInTheDocument();
    expect(screen.getByText("Open Source")).toBeInTheDocument();
  });

  it("does not render tags section when tags are empty", () => {
    const story = makeStory({ tags: [] });
    render(<StoryCard story={story} />);

    expect(screen.queryByText("LLM")).not.toBeInTheDocument();
  });

  it("renders thumbnail when image_url is provided", () => {
    const story = makeStory({ image_url: "https://example.com/img.jpg" });
    render(<StoryCard story={story} />);

    // alt="" gives it presentation role, so query by tag
    const img = document.querySelector("img");
    expect(img).not.toBeNull();
    expect(img?.getAttribute("src") ?? "").toContain(
      encodeURIComponent("https://example.com/img.jpg"),
    );
  });

  it("does not render thumbnail when image_url is absent", () => {
    const story = makeStory({ image_url: undefined });
    render(<StoryCard story={story} />);

    expect(document.querySelector("img")).toBeNull();
  });

  it("formats the date correctly", () => {
    const story = makeStory({ date: "2026-04-07" });
    render(<StoryCard story={story} />);

    expect(screen.getByText("Apr 7, 2026")).toBeInTheDocument();
  });
});
