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
    expect(screen.getByText("3 h 10 sur 5 h prévues")).toBeInTheDocument();
    const bar = screen.getByRole("progressbar", { name: "Avancement de la semaine" });
    expect(bar).toHaveAttribute("aria-valuenow", "190");
    expect(bar).toHaveAttribute("aria-valuemax", "300");
    expect(bar).toHaveAttribute("aria-valuetext", "3 h 10 sur 5 h prévues");
  });

  it("shows the tasks done and the streak", () => {
    render(<WeekCard week={WEEK} />);
    expect(screen.getByText("4 tâches sur 7 faites")).toBeInTheDocument();
    expect(screen.getByText("Série : 3 jours")).toBeInTheDocument();
  });

  it("handles one task, a one-day streak and no streak", () => {
    const { rerender } = render(<WeekCard week={{ ...WEEK, tasksDone: 1, streakDays: 1 }} />);
    expect(screen.getByText("1 tâche sur 7 faite")).toBeInTheDocument();
    expect(screen.getByText("Série : 1 jour")).toBeInTheDocument();
    rerender(<WeekCard week={{ ...WEEK, streakDays: 0 }} />);
    expect(screen.getByText("Pas de série en cours.")).toBeInTheDocument();
  });

  it("caps the bar at the planned time when the week is over target", () => {
    render(<WeekCard week={{ ...WEEK, doneMinutes: 400 }} />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "300");
    expect(screen.getByText("6 h 40 sur 5 h prévues")).toBeInTheDocument();
  });

  it("says when no program week is running or nothing is planned", () => {
    const { rerender } = render(<WeekCard week={null} />);
    expect(screen.getByText("Aucune semaine de programme en cours.")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
    rerender(<WeekCard week={{ ...WEEK, plannedMinutes: 0, doneMinutes: 0 }} />);
    expect(screen.getByText("Rien n'est prévu cette semaine.")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });
});
