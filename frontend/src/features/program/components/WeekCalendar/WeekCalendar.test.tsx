import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeWeek } from "../fixtures";
import type { WeekView } from "../viewTypes";
import { WeekCalendar } from "./WeekCalendar";

const MOVE_T1 = "Déplacer « Lire le chapitre 1 »";

/** La semaine après le déplacement de `taskId` vers `date` (ce que rend la mutation optimiste). */
function moved(week: WeekView, taskId: string, date: string): WeekView {
  const task = week.days.flatMap((day) => day.tasks).find((item) => item.id === taskId)!;
  return {
    ...week,
    days: week.days.map((day) => {
      const tasks = day.tasks.filter((item) => item.id !== taskId);
      if (day.date === date) tasks.push({ ...task, plannedDate: date });
      return { ...day, tasks };
    }),
  };
}

describe("WeekCalendar", () => {
  it("moves a task with the keyboard menu", async () => {
    const user = userEvent.setup();
    const onMoveTask = vi.fn();
    render(<WeekCalendar week={makeWeek()} editable onMoveTask={onMoveTask} />);
    await user.click(screen.getByRole("button", { name: MOVE_T1 }));
    await user.click(screen.getByRole("menuitem", { name: /mercredi 18 novembre/ }));
    expect(onMoveTask).toHaveBeenCalledWith("t1", "2026-11-18");
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("gives the focus back to the moved card once it shows in its new day", async () => {
    const user = userEvent.setup();
    const week = makeWeek();
    const { rerender } = render(<WeekCalendar week={week} editable onMoveTask={vi.fn()} />);
    screen.getByRole("button", { name: MOVE_T1 }).focus();
    await user.keyboard("{Enter}{ArrowDown}{Enter}");
    rerender(<WeekCalendar week={moved(week, "t1", "2026-11-18")} editable onMoveTask={vi.fn()} />);
    const wednesday = screen.getByRole("group", { name: /^mer\. / });
    const trigger = within(wednesday).getByRole("button", { name: MOVE_T1 });
    expect(trigger).toHaveFocus();
  });

  it("opens the menu and picks a day with the keys only", async () => {
    const user = userEvent.setup();
    const onMoveTask = vi.fn();
    render(<WeekCalendar week={makeWeek()} editable onMoveTask={onMoveTask} />);
    screen.getByRole("button", { name: MOVE_T1 }).focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("menuitem", { name: /mardi 17 novembre/ })).toHaveFocus();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onMoveTask).toHaveBeenCalledWith("t1", "2026-11-18");
  });

  it("closes the menu with Escape and gives the focus back", async () => {
    const user = userEvent.setup();
    render(<WeekCalendar week={makeWeek()} editable onMoveTask={vi.fn()} />);
    const trigger = screen.getByRole("button", { name: MOVE_T1 });
    await user.click(trigger);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(trigger).toHaveFocus();
  });

  it("does not offer the day the task is already on", async () => {
    const user = userEvent.setup();
    render(<WeekCalendar week={makeWeek()} editable onMoveTask={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: MOVE_T1 }));
    expect(screen.queryByRole("menuitem", { name: /lundi 16 novembre/ })).toBeNull();
    expect(screen.getAllByRole("menuitem")).toHaveLength(6);
  });

  it("flags a day over its capacity in text", () => {
    render(<WeekCalendar week={makeWeek()} editable onMoveTask={vi.fn()} />);
    expect(screen.getByText("Jour chargé : 150 / 120 min")).toBeInTheDocument();
    expect(screen.getAllByText("0 / 120 min").length).toBeGreaterThan(0);
  });

  it("shows seven day columns, the already-known label and the done mark", () => {
    render(<WeekCalendar week={makeWeek()} editable onMoveTask={vi.fn()} />);
    expect(
      screen.getAllByRole("group", { name: /^(lun|mar|mer|jeu|ven|sam|dim)\. / }),
    ).toHaveLength(7);
    const known = screen.getByText("Réviser les types").closest("li") as HTMLElement;
    expect(within(known).getByText("déjà acquis")).toBeInTheDocument();
    expect(within(known).getByText("Fait")).toBeInTheDocument();
  });

  it("is read-only when not editable", () => {
    render(<WeekCalendar week={makeWeek()} editable={false} onMoveTask={vi.fn()} />);
    expect(screen.getByText("Lire le chapitre 1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Déplacer/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Glisser/ })).toBeNull();
  });

  it("gives each task a drag handle announced in French", () => {
    render(<WeekCalendar week={makeWeek()} editable onMoveTask={vi.fn()} />);
    const handle = screen.getByRole("button", { name: "Glisser « Lire le chapitre 1 »" });
    expect(handle).toHaveAttribute("aria-roledescription", "tâche déplaçable");
  });
});
