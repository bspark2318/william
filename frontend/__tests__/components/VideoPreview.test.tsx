import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import VideoPreview from "@/components/VideoPreview";
import { makeVideo } from "../helpers";

describe("VideoPreview", () => {
  it("renders the video title", () => {
    const video = makeVideo({ title: "AI Weekly Recap" });
    render(<VideoPreview video={video} />);

    expect(screen.getByRole("heading", { level: 4 })).toHaveTextContent("AI Weekly Recap");
  });

  it("links to the video URL in a new tab", () => {
    const video = makeVideo({ video_url: "https://youtube.com/watch?v=xyz" });
    render(<VideoPreview video={video} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "https://youtube.com/watch?v=xyz");
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders the thumbnail image with alt text", () => {
    const video = makeVideo({
      title: "My Video",
      thumbnail_url: "https://img.youtube.com/vi/xyz/0.jpg",
    });
    render(<VideoPreview video={video} />);

    const img = screen.getByAltText("My Video");
    expect(img).toHaveAttribute("src", "https://img.youtube.com/vi/xyz/0.jpg");
  });

  it("renders description when provided", () => {
    const video = makeVideo({ description: "Deep dive into reasoning." });
    render(<VideoPreview video={video} />);

    expect(screen.getByText("Deep dive into reasoning.")).toBeInTheDocument();
  });

  it("omits description when not provided", () => {
    const video = makeVideo({ description: undefined });
    render(<VideoPreview video={video} />);

    expect(screen.queryByText("Deep dive into reasoning.")).not.toBeInTheDocument();
  });

  it("shows the featured videos section label when showLabel is true", () => {
    render(<VideoPreview video={makeVideo()} showLabel />);
    expect(screen.getByText("Featured Videos")).toBeInTheDocument();
  });
});
