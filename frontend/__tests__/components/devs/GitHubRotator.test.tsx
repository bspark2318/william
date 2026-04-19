import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import GitHubRotator from "@/components/devs/GitHubRotator";
import { makeGitHubPost } from "../../helpers";

function mockMatchMedia(reduced: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: reduced,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

describe("GitHubRotator", () => {
  beforeEach(() => {
    mockMatchMedia(false);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the first post initially", () => {
    const posts = [
      makeGitHubPost({ id: 1, repo: "foo/first" }),
      makeGitHubPost({ id: 2, repo: "bar/second" }),
    ];
    render(<GitHubRotator posts={posts} />);
    expect(screen.getByText("foo/first")).toBeInTheDocument();
    expect(screen.queryByText("bar/second")).not.toBeInTheDocument();
  });

  it("rotates to the next post after the interval", () => {
    const posts = [
      makeGitHubPost({ id: 1, repo: "foo/first" }),
      makeGitHubPost({ id: 2, repo: "bar/second" }),
    ];
    render(<GitHubRotator posts={posts} />);

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByText("bar/second")).toBeInTheDocument();
    expect(screen.queryByText("foo/first")).not.toBeInTheDocument();
  });

  it("wraps back to the first post after reaching the end", () => {
    const posts = [
      makeGitHubPost({ id: 1, repo: "foo/first" }),
      makeGitHubPost({ id: 2, repo: "bar/second" }),
    ];
    render(<GitHubRotator posts={posts} />);

    act(() => {
      vi.advanceTimersByTime(5000);
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByText("foo/first")).toBeInTheDocument();
  });

  it("renders pagination dots when there is more than one post", () => {
    const posts = [
      makeGitHubPost({ id: 1 }),
      makeGitHubPost({ id: 2 }),
      makeGitHubPost({ id: 3 }),
    ];
    render(<GitHubRotator posts={posts} />);
    const dots = screen.getAllByRole("tab");
    expect(dots).toHaveLength(3);
  });

  it("omits pagination dots with a single post", () => {
    const posts = [makeGitHubPost({ id: 1 })];
    render(<GitHubRotator posts={posts} />);
    expect(screen.queryAllByRole("tab")).toHaveLength(0);
  });

  it("jumps to the clicked dot and marks it selected", () => {
    const posts = [
      makeGitHubPost({ id: 1, repo: "foo/first" }),
      makeGitHubPost({ id: 2, repo: "bar/second" }),
      makeGitHubPost({ id: 3, repo: "baz/third" }),
    ];
    render(<GitHubRotator posts={posts} />);
    const dots = screen.getAllByRole("tab");

    act(() => {
      dots[2].click();
    });

    expect(screen.getByText("baz/third")).toBeInTheDocument();
    expect(dots[2]).toHaveAttribute("aria-selected", "true");
    expect(dots[0]).toHaveAttribute("aria-selected", "false");
  });

  it("does not auto-rotate when prefers-reduced-motion is set", () => {
    mockMatchMedia(true);
    const posts = [
      makeGitHubPost({ id: 1, repo: "foo/first" }),
      makeGitHubPost({ id: 2, repo: "bar/second" }),
    ];
    render(<GitHubRotator posts={posts} />);

    act(() => {
      vi.advanceTimersByTime(15000);
    });

    expect(screen.getByText("foo/first")).toBeInTheDocument();
    expect(screen.queryByText("bar/second")).not.toBeInTheDocument();
  });

  it("renders nothing when posts array is empty", () => {
    const { container } = render(<GitHubRotator posts={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
