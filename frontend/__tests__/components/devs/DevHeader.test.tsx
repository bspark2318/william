import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import DevHeader from "@/components/devs/DevHeader";

describe("DevHeader", () => {
  it("renders the For Developers title", () => {
    render(<DevHeader />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "For Developers",
    );
  });

  it("renders the subtitle", () => {
    render(<DevHeader />);
    expect(
      screen.getByText(/Signals to level up as an AI-era engineer/i),
    ).toBeInTheDocument();
  });

  it("renders the terminal prompt", () => {
    render(<DevHeader />);
    expect(
      screen.getByText(/cat \/context-window\/devs\/signals\.md/),
    ).toBeInTheDocument();
  });

  it("renders a back-link to /", () => {
    render(<DevHeader />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/");
  });
});
