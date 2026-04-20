import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import GitHubPostCard from "@/components/devs/GitHubPostCard";
import { makeGitHubPost } from "../../helpers";

describe("GitHubPostCard", () => {
  it("renders the repo name as a link to the repo URL", () => {
    const post = makeGitHubPost({
      repo: "anthropics/claude-agent-sdk",
      url: "https://github.com/anthropics/claude-agent-sdk",
    });
    render(<GitHubPostCard post={post} />);
    const repoLink = screen.getByRole("link", {
      name: /anthropics\/claude-agent-sdk/,
    });
    expect(repoLink).toHaveAttribute(
      "href",
      "https://github.com/anthropics/claude-agent-sdk",
    );
    expect(repoLink).toHaveAttribute("target", "_blank");
    expect(repoLink).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders the title", () => {
    const post = makeGitHubPost({ title: "v0.8.0 release" });
    render(<GitHubPostCard post={post} />);
    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent(
      "v0.8.0 release",
    );
  });

  it("renders the version tag when present", () => {
    const post = makeGitHubPost({ version: "v2.0.0" });
    render(<GitHubPostCard post={post} />);
    expect(screen.getByText(/v2\.0\.0/)).toBeInTheDocument();
  });

  it("renders release_notes_excerpt as fallback when no bullets", () => {
    const post = makeGitHubPost({
      release_bullets: undefined,
      release_notes_excerpt: "Adds sub-agent isolation.",
    });
    render(<GitHubPostCard post={post} />);
    expect(screen.getByText(/Adds sub-agent isolation/)).toBeInTheDocument();
  });

  it("renders release bullets when present and omits the excerpt", () => {
    const post = makeGitHubPost({
      release_bullets: ["Sub-agent isolation.", "New memory primitive."],
      release_notes_excerpt: "Should not appear when bullets present.",
    });
    render(<GitHubPostCard post={post} />);
    expect(screen.getByText("Sub-agent isolation.")).toBeInTheDocument();
    expect(screen.getByText("New memory primitive.")).toBeInTheDocument();
    expect(
      screen.queryByText(/Should not appear when bullets present/),
    ).not.toBeInTheDocument();
  });

  it("renders the why-it-matters one-liner when present", () => {
    const post = makeGitHubPost({
      why_it_matters: "This is the pattern teams are converging on.",
    });
    render(<GitHubPostCard post={post} />);
    expect(
      screen.getByText("This is the pattern teams are converging on."),
    ).toBeInTheDocument();
  });

  it("renders the Breaking badge when has_breaking_changes is true", () => {
    const post = makeGitHubPost({ has_breaking_changes: true });
    render(<GitHubPostCard post={post} />);
    expect(screen.getByText(/Breaking/i)).toBeInTheDocument();
  });

  it("omits the Breaking badge when has_breaking_changes is false or absent", () => {
    const post = makeGitHubPost({ has_breaking_changes: false });
    render(<GitHubPostCard post={post} />);
    expect(screen.queryByText(/Breaking/i)).not.toBeInTheDocument();
  });

  it("renders stars with thousands separator", () => {
    const post = makeGitHubPost({ stars: 14820 });
    render(<GitHubPostCard post={post} />);
    expect(screen.getByText(/14,820/)).toBeInTheDocument();
  });

  it("renders 7d stars velocity when present", () => {
    const post = makeGitHubPost({ stars_velocity_7d: 612 });
    render(<GitHubPostCard post={post} />);
    expect(screen.getByText(/\+612/)).toBeInTheDocument();
    expect(screen.getByText(/7d/)).toBeInTheDocument();
  });

  it("omits stars when absent", () => {
    const post = makeGitHubPost({ stars: undefined, stars_velocity_7d: undefined });
    render(<GitHubPostCard post={post} />);
    expect(screen.queryByText(/\/ 7d/)).not.toBeInTheDocument();
  });
});
