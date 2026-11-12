import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { makeTask, makeWeek } from "../fixtures";
import type { ProgressView } from "../viewTypes";
import { ProgressOverview } from "./ProgressOverview";

const PROGRESS: ProgressView = {
  tasksDone: 12,
  tasksPlanned: 40,
  minutesDone: 510,
  minutesPlanned: 1800,
};

describe("ProgressOverview", () => {
  it("shows done over planned hours", () => {
    render(<ProgressOverview progress={PROGRESS} weeks={[makeWeek()]} />);
    expect(screen.getByText("8 h 30 / 30 h")).toBeInTheDocument();
    expect(screen.getByText("12 / 40")).toBeInTheDocument();
  });

  it("gives the overall percentage on an accessible bar", () => {
    render(<ProgressOverview progress={PROGRESS} weeks={[makeWeek()]} />);
    const bar = screen.getByRole("progressbar", { name: "Avancement global" });
    expect(bar).toHaveAttribute("aria-valuenow", "28");
    expect(screen.getByText("28 %")).toBeInTheDocument();
  });

  it("draws one bar per week from its done tasks", () => {
    const week = makeWeek();
    const second = makeWeek({
      rank: 2,
      theme: "Les fonctions",
      days: [
        {
          date: "2026-11-23",
          capacityMinutes: 120,
          tasks: [
            makeTask({ id: "x1", minutes: 30, done: true, plannedDate: "2026-11-23" }),
            makeTask({ id: "x2", minutes: 30, plannedDate: "2026-11-23" }),
          ],
        },
      ],
    });
    render(<ProgressOverview progress={PROGRESS} weeks={[week, second]} />);
    const bars = screen.getAllByRole("progressbar", { name: /^Semaine / });
    expect(bars).toHaveLength(2);
    expect(screen.getByRole("progressbar", { name: "Semaine 2 : Les fonctions" })).toHaveAttribute(
      "aria-valuenow",
      "50",
    );
    expect(screen.getByText("30 min / 1 h")).toBeInTheDocument();
  });

  it("copes with an empty programme", () => {
    render(
      <ProgressOverview
        progress={{ tasksDone: 0, tasksPlanned: 0, minutesDone: 0, minutesPlanned: 0 }}
        weeks={[]}
      />,
    );
    expect(screen.getByText("Le programme ne contient pas encore de tâche.")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });
});
