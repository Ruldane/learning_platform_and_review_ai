import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { BriefDataView } from "../viewTypes";
import { ProjectBriefView } from "./ProjectBriefView";

const BRIEF: BriefDataView = {
  title: "Pipeline de ventes",
  objective: "Charger et agréger des ventes.",
  context: "Une boutique fictive, Société Fictive.",
  constraints: ["SQL uniquement", "Moins de 200 lignes"],
  criteria: ["Les ventes sont agrégées par mois", "Un test vérifie le total"],
  deliverable: "either",
  hours: 6,
};

describe("ProjectBriefView", () => {
  it("shows the title, the objective, the context and the expected deliverable", () => {
    render(<ProjectBriefView brief={BRIEF} />);
    expect(screen.getByRole("heading", { level: 2, name: "Pipeline de ventes" })).toBeVisible();
    expect(screen.getByText("Charger et agréger des ventes.")).toBeInTheDocument();
    expect(screen.getByText("Une boutique fictive, Société Fictive.")).toBeInTheDocument();
    expect(screen.getByText("Un lien vers un dépôt ou une description.")).toBeInTheDocument();
    expect(screen.getByText("Durée estimée : 6 h")).toBeInTheDocument();
  });

  it("lists the constraints and the numbered criteria", () => {
    render(<ProjectBriefView brief={BRIEF} />);
    const constraints = screen.getByRole("heading", { name: "Contraintes" }).parentElement!;
    expect(constraints).toHaveTextContent("SQL uniquement");
    expect(constraints).toHaveTextContent("Moins de 200 lignes");
    const criteria = screen.getByRole("heading", { name: "Critères de réussite" }).parentElement!;
    expect(criteria.querySelector("ol")).not.toBeNull();
    expect(criteria).toHaveTextContent("Un test vérifie le total");
  });

  it("leaves out a section without items", () => {
    render(<ProjectBriefView brief={{ ...BRIEF, constraints: [] }} />);
    expect(screen.queryByRole("heading", { name: "Contraintes" })).toBeNull();
  });

  it.each([
    ["repo", "Un lien vers un dépôt."],
    ["description", "Une description de ce que tu as fait."],
  ] as const)("writes the %s deliverable", (deliverable, text) => {
    render(<ProjectBriefView brief={{ ...BRIEF, deliverable }} />);
    expect(screen.getByText(text)).toBeInTheDocument();
  });
});
