import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeApplication, makeApplications } from "../fixtures";
import { KanbanBoard } from "./KanbanBoard";

const MOVE_ACME = "Déplacer « Data engineer » (Acme)";
const COLUMN = /^(À postuler|Postulée|Relancée|Entretien|Offre|Refus|Sans réponse|Retirée), \d+$/;

describe("KanbanBoard", () => {
  it("shows the eight columns in the order of the statuses, each with its count", () => {
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} />);
    const columns = screen.getAllByRole("group", { name: COLUMN });
    expect(columns.map((column) => column.getAttribute("aria-label"))).toEqual([
      "À postuler, 1",
      "Postulée, 2",
      "Relancée, 0",
      "Entretien, 1",
      "Offre, 0",
      "Refus, 0",
      "Sans réponse, 0",
      "Retirée, 0",
    ]);
  });

  it("puts each card in the column of its status and says when a column is empty", () => {
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} />);
    const applied = screen.getByRole("group", { name: "Postulée, 2" });
    expect(within(applied).getByText("Acme")).toBeInTheDocument();
    expect(within(applied).getByText("Delta")).toBeInTheDocument();
    expect(within(applied).queryByText("Beta")).toBeNull();
    expect(
      within(screen.getByRole("group", { name: "Offre, 0" })).getByText("Aucune candidature ici."),
    ).toBeInTheDocument();
  });

  it("moves a card with the Déplacer vers… menu and calls onMove", async () => {
    const user = userEvent.setup();
    const onMove = vi.fn();
    render(<KanbanBoard applications={makeApplications()} onMove={onMove} />);
    await user.click(screen.getByRole("button", { name: MOVE_ACME }));
    expect(screen.getByRole("menu", { name: "Déplacer vers…" })).toBeInTheDocument();
    await user.click(screen.getByRole("menuitem", { name: "Entretien" }));
    expect(onMove).toHaveBeenCalledWith("acme", "interview");
    expect(screen.queryByRole("menu")).toBeNull();
  });

  it("does not offer the status the card is already in", async () => {
    const user = userEvent.setup();
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: MOVE_ACME }));
    expect(screen.queryByRole("menuitem", { name: "Postulée" })).toBeNull();
    expect(screen.getAllByRole("menuitem")).toHaveLength(7);
  });

  it("moves a card with the keyboard only", async () => {
    const user = userEvent.setup();
    const onMove = vi.fn();
    render(<KanbanBoard applications={makeApplications()} onMove={onMove} />);
    screen.getByRole("button", { name: MOVE_ACME }).focus();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("menuitem", { name: "À postuler" })).toHaveFocus();
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
    const message = "« Data engineer » déplacée vers Offre.";
    expect(screen.queryByText(message)).toBeNull();
    await user.click(screen.getByRole("button", { name: MOVE_ACME }));
    await user.click(screen.getByRole("menuitem", { name: "Offre" }));
    const live = screen.getByText(message);
    expect(live).toHaveAttribute("role", "status");
    expect(live).toHaveAttribute("aria-live", "polite");
  });

  it("offers a drag handle on each card, named after the position", () => {
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} />);
    const handle = screen.getByRole("button", { name: "Glisser « Data engineer » (Acme)" });
    expect(handle).toBeInTheDocument();
    // Au doigt, le navigateur ne doit pas prendre le geste pour un défilement.
    expect(handle).toHaveClass("touch-none");
  });

  it("names the handle and the move button after the company too, for two cards with one title", () => {
    const twins = [
      makeApplication({ id: "x1", company: "Alpha", title: "Développeuse" }),
      makeApplication({ id: "x2", company: "Omega", title: "Développeuse" }),
    ];
    render(<KanbanBoard applications={twins} onMove={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Glisser « Développeuse » (Alpha)" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Glisser « Développeuse » (Omega)" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Déplacer « Développeuse » (Alpha)" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Déplacer « Développeuse » (Omega)" })).toBeVisible();
  });

  it("opens an application from its card", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<KanbanBoard applications={makeApplications()} onMove={vi.fn()} onOpen={onOpen} />);
    await user.click(
      screen.getByRole("button", { name: "Ouvrir la fiche de Beta, poste Analyste" }),
    );
    expect(onOpen).toHaveBeenCalledWith("beta");
  });

  it("is a named group", () => {
    render(<KanbanBoard applications={[]} onMove={vi.fn()} />);
    expect(
      screen.getByRole("group", { name: "Tableau de suivi des candidatures" }),
    ).toBeInTheDocument();
  });
});
