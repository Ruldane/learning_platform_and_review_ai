import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StudyStatsBadge } from "./StudyStatsBadge";

describe("StudyStatsBadge", () => {
  it("shows the streak and the week hours", () => {
    render(<StudyStatsBadge streakDays={5} weekMinutes={210} />);
    expect(screen.getByRole("list", { name: "Your study pace" })).toBeInTheDocument();
    expect(screen.getByText("Streak: 5 days")).toBeInTheDocument();
    expect(screen.getByText("This week: 3 h 30")).toBeInTheDocument();
  });

  it("formats week minutes", () => {
    const { rerender } = render(<StudyStatsBadge streakDays={2} weekMinutes={45} />);
    expect(screen.getByText("This week: 45 min")).toBeInTheDocument();
    rerender(<StudyStatsBadge streakDays={2} weekMinutes={120} />);
    expect(screen.getByText("This week: 2 h")).toBeInTheDocument();
    rerender(<StudyStatsBadge streakDays={2} weekMinutes={0} />);
    expect(screen.getByText("This week: 0 min")).toBeInTheDocument();
  });

  it("says day in the singular for one day", () => {
    render(<StudyStatsBadge streakDays={1} weekMinutes={30} />);
    expect(screen.getByText("Streak: 1 day")).toBeInTheDocument();
  });

  it("says plainly that there is no streak", () => {
    render(<StudyStatsBadge streakDays={0} weekMinutes={0} />);
    expect(screen.getByText("No active streak")).toBeInTheDocument();
  });

  it("uses text and hidden icons, never an emoji", () => {
    const { container } = render(<StudyStatsBadge streakDays={7} weekMinutes={90} />);
    expect(container.textContent).not.toMatch(/\p{Extended_Pictographic}/u);
    const icons = container.querySelectorAll("svg");
    expect(icons.length).toBeGreaterThan(0);
    icons.forEach((icon) => expect(icon).toHaveAttribute("aria-hidden", "true"));
  });
});
