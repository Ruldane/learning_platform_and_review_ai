import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { WeekView } from "../viewTypes";
import { WeekCard } from "./WeekCard";

const WEEK: WeekView = {
  doneMinutes: 190,
  plannedMinutes: 300,
  streakDays: 3,
  tasksDone: 4,
  tasksTotal: 7,
};

describe("WeekCard", () => {
  it("writes the progress in words and shows it as a bar", () => {
    render(<WeekCard week={WEEK} />);
    expect(screen.getByText("3 h 10 of 5 h planned")).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Week progress" });
    expect(bar).toHaveAttribute("aria-valuenow", "190");
    expect(bar).toHaveAttribute("aria-valuemax", "300");
    expect(bar).toHaveAttribute("aria-valuetext", "3 h 10 of 5 h planned");
  });

  it("shows the tasks done and the streak", () => {
    render(<WeekCard week={WEEK} />);
    expect(screen.getByText("4 of 7 tasks done")).toBeInTheDocument();
    expect(screen.getByText("Streak: 3 days")).toBeInTheDocument();
  });

  it("handles one task, a one-day streak and no streak", () => {
    const { rerender } = render(<WeekCard week={{ ...WEEK, tasksDone: 1, streakDays: 1 }} />);
    expect(screen.getByText("1 of 7 tasks done")).toBeInTheDocument();
    expect(screen.getByText("Streak: 1 day")).toBeInTheDocument();
    rerender(<WeekCard week={{ ...WEEK, streakDays: 0 }} />);
    expect(screen.getByText("No active streak.")).toBeInTheDocument();
  });

  it("caps the bar at the planned time when the week is over target", () => {
    render(<WeekCard week={{ ...WEEK, doneMinutes: 400 }} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "300");
    expect(screen.getByText("6 h 40 of 5 h planned")).toBeInTheDocument();
  });

  it("says when no program week is running or nothing is planned", () => {
    const { rerender } = render(<WeekCard week={null} />);
    expect(screen.getByText("No program week in progress.")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
    rerender(<WeekCard week={{ ...WEEK, plannedMinutes: 0, doneMinutes: 0 }} />);
    expect(screen.getByText("Nothing planned this week.")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });

  it("says the rubric is unavailable instead of « no week » when its source failed", () => {
    render(<WeekCard week={null} unavailable />);
    expect(screen.getByText("Section unavailable this morning.")).toBeInTheDocument();
    expect(screen.queryByText("No program week in progress.")).toBeNull();
  });
});
