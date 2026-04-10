import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Masthead from "@/components/Masthead";

describe("Masthead", () => {
  it("renders the site title", () => {
    render(<Masthead weekOf="2026-04-07" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("The Context Window");
  });

  it("renders a formatted date", () => {
    render(<Masthead weekOf="2026-04-07" />);
    expect(screen.getByText(/April.*7.*2026/)).toBeInTheDocument();
  });

  it("renders issue number when provided", () => {
    render(<Masthead weekOf="2026-04-07" issueNumber={3} />);
    expect(screen.getByText(/No\.\s*3/)).toBeInTheDocument();
  });

  it("omits issue number when not provided", () => {
    render(<Masthead weekOf="2026-04-07" />);
    expect(screen.queryByText(/No\./)).not.toBeInTheDocument();
  });

  it("renders the issue title when provided", () => {
    render(<Masthead weekOf="2026-04-07" title="Big AI Week" />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Big AI Week");
  });

  it("omits the issue title when not provided", () => {
    render(<Masthead weekOf="2026-04-07" />);
    expect(screen.queryByRole("heading", { level: 2 })).not.toBeInTheDocument();
  });

  it("shows the Weekly Edition label", () => {
    render(<Masthead weekOf="2026-04-07" />);
    expect(screen.getByText(/Weekly Edition/)).toBeInTheDocument();
  });
});
