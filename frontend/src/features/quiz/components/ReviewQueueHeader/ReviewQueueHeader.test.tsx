import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReviewQueueHeader } from "./ReviewQueueHeader";

describe("ReviewQueueHeader", () => {
  it("shows what is left, what is done and the 15 minute cap", () => {
    render(<ReviewQueueHeader remaining={12} reviewedToday={8} dailyCards={30} />);
    expect(screen.getByText("12 cards to review")).toBeInTheDocument();
    expect(screen.getByText("Reviewed today: 8 of 30")).toBeInTheDocument();
    expect(screen.getByText("15 min max")).toBeInTheDocument();
  });

  it("exposes the daily progress", () => {
    render(<ReviewQueueHeader remaining={12} reviewedToday={8} dailyCards={30} />);
    const bar = screen.getByRole("progressbar", { name: "Cards reviewed today" });
    expect(bar).toHaveAttribute("aria-valuenow", "8");
    expect(bar).toHaveAttribute("aria-valuemax", "30");
  });

  it("uses the singular for one card", () => {
    render(<ReviewQueueHeader remaining={1} reviewedToday={0} dailyCards={30} />);
    expect(screen.getByText("1 card to review")).toBeInTheDocument();
  });

  it("says nothing is left", () => {
    render(<ReviewQueueHeader remaining={0} reviewedToday={30} dailyCards={30} />);
    expect(screen.getByText("No more cards to review")).toBeInTheDocument();
  });

  it("caps the bar at the daily limit", () => {
    render(<ReviewQueueHeader remaining={3} reviewedToday={35} dailyCards={30} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "30");
  });
});
