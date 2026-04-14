import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import WeekNav from "@/components/WeekNav";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe("WeekNav", () => {
  beforeEach(() => mockPush.mockClear());

  it("renders Previous button when prevIssueId is provided", () => {
    render(<WeekNav prevIssueId={1} prevLabel="2026-03-31" />);
    expect(screen.getByRole("button", { name: /previous/i })).toBeInTheDocument();
  });

  it("renders Next button when nextIssueId is provided", () => {
    render(<WeekNav nextIssueId={3} nextLabel="2026-04-14" />);
    expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
  });

  it("hides Previous button when prevIssueId is undefined", () => {
    render(<WeekNav nextIssueId={3} />);
    expect(screen.queryByRole("button", { name: /previous/i })).not.toBeInTheDocument();
  });

  it("hides Next button when nextIssueId is undefined", () => {
    render(<WeekNav prevIssueId={1} />);
    expect(screen.queryByRole("button", { name: /next/i })).not.toBeInTheDocument();
  });

  it("navigates to previous issue on click", async () => {
    render(<WeekNav prevIssueId={2} />);
    screen.getByRole("button", { name: /previous/i }).click();
    expect(mockPush).toHaveBeenCalledWith("/?issue=2");
  });

  it("navigates to next issue on click", async () => {
    render(<WeekNav nextIssueId={5} />);
    screen.getByRole("button", { name: /next/i }).click();
    expect(mockPush).toHaveBeenCalledWith("/?issue=5");
  });

  it("always shows the 'Latest Edition' label", () => {
    render(<WeekNav />);
    expect(screen.getByText(/latest edition/i)).toBeInTheDocument();
  });
});
