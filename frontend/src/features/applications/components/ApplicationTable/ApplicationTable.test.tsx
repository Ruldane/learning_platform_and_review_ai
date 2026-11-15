import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { makeApplications } from "../fixtures";
import { ApplicationTable } from "./ApplicationTable";

function companies(): string[] {
  const rows = screen.getAllByRole("row").slice(1);
  return rows.map((row) => within(row).getAllByRole("cell")[0]?.textContent ?? "");
}

function header(name: RegExp): HTMLElement {
  return screen.getByRole("columnheader", { name });
}

describe("ApplicationTable", () => {
  it("shows the six columns and one row per application", () => {
    render(<ApplicationTable applications={makeApplications()} onOpen={vi.fn()} />);
    expect(screen.getAllByRole("columnheader").map((item) => item.textContent)).toEqual([
      "Entreprise",
      "Poste",
      "Statut",
      "Candidature",
      "Prochaine action",
      "Relances dues",
    ]);
    expect(screen.getAllByRole("row")).toHaveLength(5);
    const acme = within(screen.getByRole("row", { name: /Acme/ }));
    expect(acme.getByText("Postulée")).toBeInTheDocument();
    expect(acme.getByText("03/11/2026")).toBeInTheDocument();
    expect(acme.getByText("Relancer (20/11/2026)")).toBeInTheDocument();
    expect(acme.getByText("2")).toBeInTheDocument();
  });

  it("starts in the given order with no column marked as sorted", () => {
    render(<ApplicationTable applications={makeApplications()} onOpen={vi.fn()} />);
    for (const item of screen.getAllByRole("columnheader")) {
      expect(item).toHaveAttribute("aria-sort", "none");
    }
    expect(companies()).toEqual(["Acme", "Beta", "Gamma", "Delta"]);
  });

  it("sorts by a column on click, then reverses on the next click, with aria-sort", async () => {
    const user = userEvent.setup();
    render(<ApplicationTable applications={makeApplications()} onOpen={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Trier par Entreprise" }));
    expect(header(/Entreprise/)).toHaveAttribute("aria-sort", "ascending");
    expect(companies()).toEqual(["Acme", "Beta", "Delta", "Gamma"]);
    await user.click(screen.getByRole("button", { name: "Trier par Entreprise" }));
    expect(header(/Entreprise/)).toHaveAttribute("aria-sort", "descending");
    expect(companies()).toEqual(["Gamma", "Delta", "Beta", "Acme"]);
  });

  it("marks only the sorted column and resets the others", async () => {
    const user = userEvent.setup();
    render(<ApplicationTable applications={makeApplications()} onOpen={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Trier par Entreprise" }));
    await user.click(screen.getByRole("button", { name: "Trier par Poste" }));
    expect(header(/Entreprise/)).toHaveAttribute("aria-sort", "none");
    expect(header(/Poste/)).toHaveAttribute("aria-sort", "ascending");
  });

  it("sorts the statuses in the order of the board, not alphabetically", async () => {
    const user = userEvent.setup();
    render(<ApplicationTable applications={makeApplications()} onOpen={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Trier par Statut" }));
    expect(companies()).toEqual(["Beta", "Acme", "Delta", "Gamma"]);
  });

  it("sorts the dates and keeps the applications without a date at the end in both directions", async () => {
    const user = userEvent.setup();
    render(<ApplicationTable applications={makeApplications()} onOpen={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Trier par Candidature" }));
    expect(companies()).toEqual(["Gamma", "Acme", "Delta", "Beta"]);
    await user.click(screen.getByRole("button", { name: "Trier par Candidature" }));
    expect(companies()).toEqual(["Delta", "Acme", "Gamma", "Beta"]);
  });

  it("sorts the due reminders as numbers", async () => {
    const user = userEvent.setup();
    render(<ApplicationTable applications={makeApplications()} onOpen={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: "Trier par Relances dues" }));
    await user.click(screen.getByRole("button", { name: "Trier par Relances dues" }));
    expect(companies()[0]).toBe("Acme");
  });

  it("opens an application from its company", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    render(<ApplicationTable applications={makeApplications()} onOpen={onOpen} />);
    await user.click(
      screen.getByRole("button", { name: "Ouvrir la fiche de Gamma, poste Chef de projet" }),
    );
    expect(onOpen).toHaveBeenCalledWith("gamma");
  });

  it("says so when there is no application", () => {
    render(<ApplicationTable applications={[]} onOpen={vi.fn()} />);
    expect(screen.getByText("Aucune candidature pour l'instant.")).toBeInTheDocument();
  });
});
