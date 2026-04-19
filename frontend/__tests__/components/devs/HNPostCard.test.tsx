import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import HNPostCard from "@/components/devs/HNPostCard";
import { makeHNPost } from "../../helpers";

describe("HNPostCard", () => {
  it("renders the title linking to the article URL", () => {
    const post = makeHNPost({
      title: "A field guide to LLM evals",
      url: "https://hamel.dev/blog/evals",
    });
    render(<HNPostCard post={post} />);
    const titleLink = screen.getByRole("link", {
      name: /A field guide to LLM evals/,
    });
    expect(titleLink).toHaveAttribute("href", "https://hamel.dev/blog/evals");
    expect(titleLink).toHaveAttribute("target", "_blank");
    expect(titleLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders points and comment count", () => {
    const post = makeHNPost({ points: 843, comments: 214 });
    render(<HNPostCard post={post} />);
    expect(screen.getByText(/843/)).toBeInTheDocument();
    expect(screen.getByText(/214 comments/)).toBeInTheDocument();
  });

  it("links the comment count to the HN discussion page", () => {
    const post = makeHNPost({ hn_url: "https://news.ycombinator.com/item?id=42" });
    render(<HNPostCard post={post} />);
    const commentsLink = screen.getByRole("link", { name: /comments/i });
    expect(commentsLink).toHaveAttribute(
      "href",
      "https://news.ycombinator.com/item?id=42",
    );
  });

  it("renders thread summary bullets when present", () => {
    const post = makeHNPost({
      bullets: ["First point.", "Second point.", "Third point."],
    });
    render(<HNPostCard post={post} />);
    expect(screen.getByText("First point.")).toBeInTheDocument();
    expect(screen.getByText("Second point.")).toBeInTheDocument();
    expect(screen.getByText("Third point.")).toBeInTheDocument();
  });

  it("falls back to top comment excerpt when bullets are absent", () => {
    const post = makeHNPost({
      bullets: undefined,
      top_comment_excerpt: "This changed how I think about evals.",
    });
    render(<HNPostCard post={post} />);
    expect(
      screen.getByText(/This changed how I think about evals/),
    ).toBeInTheDocument();
  });

  it("prefers bullets over top comment when both are present", () => {
    const post = makeHNPost({
      bullets: ["Bullet point content."],
      top_comment_excerpt: "Quote content.",
    });
    render(<HNPostCard post={post} />);
    expect(screen.getByText("Bullet point content.")).toBeInTheDocument();
    expect(screen.queryByText("Quote content.")).not.toBeInTheDocument();
  });

  it("renders nothing below metadata when both bullets and top comment are absent", () => {
    const post = makeHNPost({
      bullets: undefined,
      top_comment_excerpt: undefined,
    });
    render(<HNPostCard post={post} />);
    expect(document.querySelector("blockquote")).toBeNull();
    expect(document.querySelector("ul")).toBeNull();
  });
});
