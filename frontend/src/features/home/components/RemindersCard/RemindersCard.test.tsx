import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ReminderItemView } from "../viewTypes";
import { RemindersCard } from "./RemindersCard";

const ITEMS: ReminderItemView[] = [
  {
    id: "r1",
    applicationId: "a1",
    company: "Société Fictive",
    title: "Data engineer",
    dueOn: "2026-11-16",
  },
  { id: "r2", applicationId: "a2", company: "Autre SA", title: "Analyste", dueOn: "2026-11-17" },
];

describe("RemindersCard", () => {
  it("lists the company, the position and the due date of each reminder", () => {
    render(<RemindersCard due={2} items={ITEMS} onOpen={vi.fn()} />);
    const list = screen.getByRole("list", { name: "Follow-ups to do" });
    expect(list).toHaveTextContent("Société Fictive, Data engineer role");
    expect(list).toHaveTextContent("due on Mon 16 Nov");
    expect(list).toHaveTextContent("Autre SA, Analyste role");
  });

  it("opens the application of the reminder that is clicked", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<RemindersCard due={2} items={ITEMS} onOpen={onOpen} />);
    await user.click(screen.getByRole("button", { name: "Autre SA, Analyste role" }));
    expect(onOpen).toHaveBeenCalledWith("a2");
  });

  it("says how many more reminders are due beyond the ones shown", () => {
    render(<RemindersCard due={7} items={ITEMS} onOpen={vi.fn()} />);
    expect(screen.getByText("5 more follow-ups due.")).toBeInTheDocument();
  });

  it("gives the count, without an empty list, when reminders are due but none is listed", () => {
    render(<RemindersCard due={3} items={[]} onOpen={vi.fn()} />);
    expect(screen.getByText("3 follow-ups due.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.queryByText(/more follow-ups/)).toBeNull();
  });

  it("says there is nothing due", () => {
    render(<RemindersCard due={0} items={[]} onOpen={vi.fn()} />);
    expect(screen.getByText("No follow-ups due.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it("says the rubric is unavailable instead of a false zero when its source failed", () => {
    render(<RemindersCard due={0} items={[]} unavailable onOpen={vi.fn()} />);
    expect(screen.getByText("Section unavailable this morning.")).toBeInTheDocument();
    expect(screen.queryByText("No follow-ups due.")).toBeNull();
  });
});
