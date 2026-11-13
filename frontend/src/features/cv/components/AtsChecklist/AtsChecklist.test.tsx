import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AtsCheckView } from "../viewTypes";
import { AtsChecklist } from "./AtsChecklist";

const CHECKS: AtsCheckView[] = [
  { id: "selectable_text", passed: true, detail: "Le texte se sélectionne." },
  { id: "reading_order", passed: true, detail: "L'ordre de lecture est celui de la page." },
  { id: "standard_headings", passed: false, detail: "Titre « Mon parcours » non standard." },
  { id: "contact_in_body", passed: true, detail: "Coordonnées dans le corps." },
  { id: "font_sizes", passed: true, detail: "Aucune taille sous 9 pt." },
];

describe("AtsChecklist", () => {
  it("lists the five checks with their verdict written out and their detail", () => {
    render(<AtsChecklist checks={CHECKS} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(5);
    const headings = within(items[2] as HTMLElement);
    expect(headings.getByText("Titres de sections standard")).toBeInTheDocument();
    expect(headings.getByText("À revoir")).toBeInTheDocument();
    expect(headings.getByText("Titre « Mon parcours » non standard.")).toBeInTheDocument();
    expect(within(items[0] as HTMLElement).getByText("Réussi")).toBeInTheDocument();
  });

  it("always shows the fixed mention that nothing guarantees passing", () => {
    render(<AtsChecklist checks={CHECKS} />);
    expect(
      screen.getByText("Aucun outil ne garantit le passage d'un logiciel de recrutement."),
    ).toBeInTheDocument();
  });

  it("keeps the mention, and says so, when there is no check", () => {
    render(<AtsChecklist checks={[]} />);
    expect(screen.getByText("Aucun contrôle pour l'instant.")).toBeInTheDocument();
    expect(screen.getByText(/Aucun outil ne garantit/)).toBeInTheDocument();
  });

  it("is a named region", () => {
    render(<AtsChecklist checks={CHECKS} />);
    expect(
      screen.getByRole("region", { name: "Lisibilité par un logiciel de recrutement" }),
    ).toBeInTheDocument();
  });
});
