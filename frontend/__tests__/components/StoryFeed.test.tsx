import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import StoryFeed from "@/components/StoryFeed";
import { makeStory } from "../helpers";

describe("StoryFeed", () => {
  it("renders all stories", () => {
    const stories = [
      makeStory({ id: 1, title: "Story A", display_order: 1 }),
      makeStory({ id: 2, title: "Story B", display_order: 2 }),
      makeStory({ id: 3, title: "Story C", display_order: 3 }),
    ];
    render(<StoryFeed stories={stories} />);

    expect(screen.getByText("Story A")).toBeInTheDocument();
    expect(screen.getByText("Story B")).toBeInTheDocument();
    expect(screen.getByText("Story C")).toBeInTheDocument();
  });

  it("renders stories in display_order regardless of input order", () => {
    const stories = [
      makeStory({ id: 3, title: "Third", display_order: 3 }),
      makeStory({ id: 1, title: "First", display_order: 1 }),
      makeStory({ id: 2, title: "Second", display_order: 2 }),
    ];
    render(<StoryFeed stories={stories} />);

    const headings = screen.getAllByRole("heading", { level: 3 });
    expect(headings[0]).toHaveTextContent("First");
    expect(headings[1]).toHaveTextContent("Second");
    expect(headings[2]).toHaveTextContent("Third");
  });

  it("renders nothing for empty stories array", () => {
    const { container } = render(<StoryFeed stories={[]} />);
    expect(container.querySelectorAll("article")).toHaveLength(0);
  });
});
