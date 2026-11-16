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
    const list = screen.getByRole("list", { name: "Relances à faire" });
    expect(list).toHaveTextContent("Société Fictive, poste Data engineer");
    expect(list).toHaveTextContent("à faire le lun. 16 nov.");
    expect(list).toHaveTextContent("Autre SA, poste Analyste");
  });

  it("opens the application of the reminder that is clicked", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<RemindersCard due={2} items={ITEMS} onOpen={onOpen} />);
    await user.click(screen.getByRole("button", { name: "Autre SA, poste Analyste" }));
    expect(onOpen).toHaveBeenCalledWith("a2");
  });

  it("says how many more reminders are due beyond the ones shown", () => {
    render(<RemindersCard due={7} items={ITEMS} onOpen={vi.fn()} />);
    expect(screen.getByText("5 autres relances dues.")).toBeInTheDocument();
  });

  it("gives the count, without an empty list, when reminders are due but none is listed", () => {
    render(<RemindersCard due={3} items={[]} onOpen={vi.fn()} />);
    expect(screen.getByText("3 relances dues.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.queryByText(/autres relances/)).toBeNull();
  });

  it("says there is nothing due", () => {
    render(<RemindersCard due={0} items={[]} onOpen={vi.fn()} />);
    expect(screen.getByText("Aucune relance due.")).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });
});
