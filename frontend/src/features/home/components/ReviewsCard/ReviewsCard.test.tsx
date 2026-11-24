import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ReviewsCard } from "./ReviewsCard";

describe("ReviewsCard", () => {
  it("says how many cards are in today's queue and how many are due beyond it", () => {
    render(<ReviewsCard queue={12} remaining={5} onReview={vi.fn()} />);
    expect(screen.getByRole("heading", { level: 2, name: "Reviews" })).toBeVisible();
    expect(screen.getByText("12 cards to review today.")).toBeInTheDocument();
    expect(
      screen.getByText("5 more cards are due beyond today's queue."),
    ).toBeInTheDocument();
  });

  it("uses the singular for one card", () => {
    render(<ReviewsCard queue={1} remaining={1} onReview={vi.fn()} />);
    expect(screen.getByText("1 card to review today.")).toBeInTheDocument();
    expect(
      screen.getByText("1 more card is due beyond today's queue."),
    ).toBeInTheDocument();
  });

  it("opens the reviews from its button with the keyboard", async () => {
    const user = userEvent.setup();
    const onReview = vi.fn();
    render(<ReviewsCard queue={3} remaining={0} onReview={onReview} />);
    await user.tab();
    expect(screen.getByRole("button", { name: "Review" })).toHaveFocus();
    await user.keyboard(" ");
    expect(onReview).toHaveBeenCalledOnce();
    expect(screen.queryByText(/beyond today's queue/)).toBeNull();
  });

  it("says there is nothing to review and offers no button", () => {
    render(<ReviewsCard queue={0} remaining={0} onReview={vi.fn()} />);
    expect(screen.getByText("No reviews due today.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("says the rubric is unavailable instead of a false zero, without a review button", () => {
    render(<ReviewsCard queue={0} remaining={0} unavailable onReview={vi.fn()} />);
    expect(screen.getByText("Section unavailable this morning.")).toBeInTheDocument();
    expect(screen.queryByText("No reviews due today.")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
