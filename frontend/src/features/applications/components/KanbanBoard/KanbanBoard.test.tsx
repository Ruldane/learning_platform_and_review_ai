import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeApplication, makeApplications } from "../fixtures";
import { KanbanBoard } from "./KanbanBoard";

const MOVE_ACME = "Move “Data engineer” (Acme)";
const COLUMN = /^(To apply|Applied|Followed up|Interview|Offer|Rejected|No answer|Withdrawn), \d+$/;

describe("KanbanBoard", () => {
  it("shows the eight columns in the order of the statuses, each with its count", () => {
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} />);
    const columns = screen.getAllByRole("group", { name: COLUMN });
    expect(columns.map((column) => column.getAttribute("aria-label"))).toEqual([
      "To apply, 1",
      "Applied, 2",
      "Followed up, 0",
      "Interview, 1",
      "Offer, 0",
      "Rejected, 0",
      "No answer, 0",
      "Withdrawn, 0",
    ]);
  });

  it("puts each card in the column of its status and says when a column is empty", () => {
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} />);
    const applied = screen.getByRole("group", { name: "Applied, 2" });
    expect(within(applied).getByText("Acme")).toBeInTheDocument();
    expect(within(applied).getByText("Delta")).toBeInTheDocument();
    expect(within(applied).queryByText("Beta")).toBeNull();
    expect(
      within(screen.getByRole("group", { name: "Offer, 0" })).getByText("No applications here."),
    ).toBeInTheDocument();
  });

  it("moves a card with the Move to… menu and calls onMove", async () => {
    const user = userEvent.setup();
    const onMove = vi.fn();
    render(<KanbanBoard applications={makeApplications()} onMove={onMove} />);
    await user.click(screen.getByRole("button", { name: MOVE_ACME }));
    expect(screen.getByRole("menu", { name: "Move to…" })).toBeInTheDocument();
    await user.click(screen.getByRole("menuitem", { name: "Interview" }));
    expect(onMove).toHaveBeenCalledWith("acme", "interview");
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("does not offer the status the card is already in", async () => {
    const user = userEvent.setup();
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: MOVE_ACME }));
    expect(screen.queryByRole("menuitem", { name: "Applied" })).toBeNull();
    expect(screen.getAllByRole("menuitem")).toHaveLength(7);
  });

  it("moves a card with the keyboard only", async () => {
    const user = userEvent.setup();
    const onMove = vi.fn();
    render(<KanbanBoard applications={makeApplications()} onMove={onMove} />);
    screen.getByRole("button", { name: MOVE_ACME }).focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("menuitem", { name: "To apply" })).toHaveFocus();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onMove).toHaveBeenCalledWith("acme", "followed_up");
  });

  it("closes the menu with Escape and gives the focus back to its button", async () => {
    const user = userEvent.setup();
    const onMove = vi.fn();
    render(<KanbanBoard applications={makeApplications()} onMove={onMove} />);
    const trigger = screen.getByRole("button", { name: MOVE_ACME });
    await user.click(trigger);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).toBeNull();
    expect(trigger).toHaveFocus();
    expect(onMove).not.toHaveBeenCalled();
  });

  it("announces the move in a live region", async () => {
    const user = userEvent.setup();
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} />);
    const message = "“Data engineer” moved to Offer.";
    expect(screen.queryByText(message)).toBeNull();
    await user.click(screen.getByRole("button", { name: MOVE_ACME }));
    await user.click(screen.getByRole("menuitem", { name: "Offer" }));
    const live = screen.getByText(message);
    expect(live).toHaveAttribute("role", "status");
    expect(live).toHaveAttribute("aria-live", "polite");
  });

  it("offers a drag handle on each card, named after the position", () => {
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} />);
    const handle = screen.getByRole("button", { name: "Drag “Data engineer” (Acme)" });
    expect(handle).toBeInTheDocument();
    // A touch drag on the handle should move the card.
    expect(handle).toHaveClass("touch-none");
  });

  it("names the handle and the move button after the company too, for two cards with one title", () => {
    const twins = [
      makeApplication({ id: "x1", company: "Alpha", title: "Développeuse" }),
      makeApplication({ id: "x2", company: "Omega", title: "Développeuse" }),
    ];
    render(<KanbanBoard applications={twins} onMove={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Drag “Développeuse” (Alpha)" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Drag “Développeuse” (Omega)" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Move “Développeuse” (Alpha)" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Move “Développeuse” (Omega)" })).toBeVisible();
  });

  it("opens an application from its card", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} onOpen={onOpen} />);
    await user.click(
      screen.getByRole("button", { name: "Open the Beta application, Analyste role" }),
    );
    expect(onOpen).toHaveBeenCalledWith("beta");
  });

  it("is a named group", () => {
    render(<KanbanBoard applications={[]} onMove={vi.fn()} />);
    expect(
      screen.getByRole("group", { name: "Application tracking board" }),
    ).toBeInTheDocument();
  });
});
