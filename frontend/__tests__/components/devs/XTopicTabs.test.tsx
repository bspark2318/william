import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import XTopicTabs from "@/components/devs/XTopicTabs";
import { makeXTopicDigest } from "../../helpers";

describe("XTopicTabs", () => {
  it("renders the first topic's bullets initially", () => {
    const topics = [
      makeXTopicDigest({
        id: 1,
        topic: "evals",
        bullets: [
          {
            text: "Evals first.",
            sources: [
              { url: "https://x.com/a/1", author_handle: "karpathy" },
            ],
          },
        ],
      }),
      makeXTopicDigest({
        id: 2,
        topic: "agents",
        bullets: [
          {
            text: "Narrow and deep.",
            sources: [{ url: "https://x.com/b/2", author_handle: "swyx" }],
          },
        ],
      }),
    ];
    render(<XTopicTabs topics={topics} />);
    expect(screen.getByText("Evals first.")).toBeInTheDocument();
    expect(screen.queryByText("Narrow and deep.")).not.toBeInTheDocument();
  });

  it("renders one tab per topic with # prefix", () => {
    const topics = [
      makeXTopicDigest({ id: 1, topic: "evals" }),
      makeXTopicDigest({ id: 2, topic: "agents" }),
      makeXTopicDigest({ id: 3, topic: "mcp" }),
    ];
    render(<XTopicTabs topics={topics} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toHaveTextContent("evals");
    expect(tabs[1]).toHaveTextContent("agents");
    expect(tabs[2]).toHaveTextContent("mcp");
  });

  it("marks the first tab selected by default", () => {
    const topics = [
      makeXTopicDigest({ id: 1, topic: "evals" }),
      makeXTopicDigest({ id: 2, topic: "agents" }),
    ];
    render(<XTopicTabs topics={topics} />);
    const tabs = screen.getAllByRole("tab");
    expect(tabs[0]).toHaveAttribute("aria-selected", "true");
    expect(tabs[1]).toHaveAttribute("aria-selected", "false");
  });

  it("switches to the clicked tab's bullets and updates aria-selected", () => {
    const topics = [
      makeXTopicDigest({
        id: 1,
        topic: "evals",
        bullets: [{ text: "Evals first.", sources: [] }],
      }),
      makeXTopicDigest({
        id: 2,
        topic: "agents",
        bullets: [{ text: "Narrow and deep.", sources: [] }],
      }),
    ];
    render(<XTopicTabs topics={topics} />);
    const tabs = screen.getAllByRole("tab");

    act(() => {
      tabs[1].click();
    });

    expect(screen.getByText("Narrow and deep.")).toBeInTheDocument();
    expect(screen.queryByText("Evals first.")).not.toBeInTheDocument();
    expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    expect(tabs[0]).toHaveAttribute("aria-selected", "false");
  });

  it("renders all bullets and source links for the active topic", () => {
    const topics = [
      makeXTopicDigest({
        id: 1,
        topic: "evals",
        bullets: [
          {
            text: "First bullet.",
            sources: [
              {
                url: "https://x.com/karpathy/status/1",
                author_handle: "karpathy",
              },
              {
                url: "https://x.com/HamelHusain/status/2",
                author_handle: "HamelHusain",
              },
            ],
          },
          {
            text: "Second bullet.",
            sources: [
              { url: "https://x.com/simonw/status/3", author_handle: "simonw" },
            ],
          },
        ],
      }),
    ];
    render(<XTopicTabs topics={topics} />);
    expect(screen.getByText("First bullet.")).toBeInTheDocument();
    expect(screen.getByText("Second bullet.")).toBeInTheDocument();
    const karpathyLink = screen.getByText("@karpathy");
    expect(karpathyLink).toHaveAttribute(
      "href",
      "https://x.com/karpathy/status/1",
    );
    expect(karpathyLink).toHaveAttribute("target", "_blank");
    expect(karpathyLink).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText("@HamelHusain")).toBeInTheDocument();
    expect(screen.getByText("@simonw")).toBeInTheDocument();
  });

  it("hides the tab strip when there is only one topic", () => {
    const topics = [
      makeXTopicDigest({
        id: 1,
        topic: "evals",
        bullets: [{ text: "Only one.", sources: [] }],
      }),
    ];
    render(<XTopicTabs topics={topics} />);
    expect(screen.queryAllByRole("tab")).toHaveLength(0);
    expect(screen.getByText("Only one.")).toBeInTheDocument();
  });

  it("renders nothing when topics array is empty", () => {
    const { container } = render(<XTopicTabs topics={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
