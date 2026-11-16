import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EvaluationDataView } from "../viewTypes";
import { EvaluationView } from "./EvaluationView";

const CRITERIA = ["Ventes agrégées par mois", "Un test vérifie le total", "README clair"];

const EVALUATION: EvaluationDataView = {
  verdict: "to_redo",
  feedback: "Le total n'est pas testé.",
  repoStatus: "read",
  hasScreenshots: false,
  results: [
    { index: 1, met: true, comment: "Correct." },
    { index: 2, met: false, comment: "Aucun test." },
    { index: 3, met: true, comment: "" },
  ],
};

const renderView = (evaluation: EvaluationDataView = EVALUATION) =>
  render(<EvaluationView evaluation={evaluation} criteria={CRITERIA} />);

const items = () =>
  within(screen.getByRole("list", { name: "Critères de réussite" })).getAllByRole("listitem");

describe("EvaluationView", () => {
  it("writes the verdict, the feedback and every criterion", () => {
    renderView();
    expect(
      screen.getByRole("heading", { level: 2, name: "Évaluation du Praticien" }),
    ).toBeVisible();
    expect(screen.getByText("Projet à refaire")).toBeInTheDocument();
    expect(screen.getByText("Le total n'est pas testé.")).toBeInTheDocument();
    expect(screen.getByText("Ventes agrégées par mois")).toBeInTheDocument();
    expect(screen.getAllByText("Atteint")).toHaveLength(2);
    expect(screen.getByText("Non atteint")).toBeInTheDocument();
  });

  it("pairs each criterion with the result that carries its number, whatever the order", () => {
    renderView({
      ...EVALUATION,
      results: [
        { index: 3, met: false, comment: "README absent." },
        { index: 1, met: true, comment: "Correct." },
        { index: 2, met: true, comment: "Test présent." },
      ],
    });
    expect(items()[0]).toHaveTextContent("Ventes agrégées par mois");
    expect(items()[0]).toHaveTextContent("Atteint");
    expect(items()[0]).toHaveTextContent("Correct.");
    expect(items()[1]).toHaveTextContent("Un test vérifie le total");
    expect(items()[1]).toHaveTextContent("Test présent.");
    expect(items()[2]).toHaveTextContent("README clair");
    expect(items()[2]).toHaveTextContent("Non atteint");
    expect(items()[2]).toHaveTextContent("README absent.");
  });

  it("shows « Pas encore évalué » for a criterion without result, and ignores an unknown index", () => {
    renderView({
      ...EVALUATION,
      results: [
        { index: 2, met: true, comment: "Test présent." },
        { index: 7, met: false, comment: "Hors énoncé." },
        { index: 0, met: false, comment: "Zéro." },
      ],
    });
    expect(items()).toHaveLength(3);
    expect(items()[0]).toHaveTextContent("Pas encore évalué");
    expect(items()[1]).toHaveTextContent("Atteint");
    expect(items()[2]).toHaveTextContent("Pas encore évalué");
    expect(screen.queryByText("Hors énoncé.")).toBeNull();
    expect(screen.queryByText("Zéro.")).toBeNull();
  });

  it("writes a validated verdict", () => {
    renderView({ ...EVALUATION, verdict: "validated" });
    expect(screen.getByText("Projet validé")).toBeInTheDocument();
  });

  it("says that the screenshots were not read when there are some", () => {
    const { rerender } = renderView();
    expect(screen.queryByText("Captures non lues par le Praticien.")).toBeNull();
    rerender(
      <EvaluationView evaluation={{ ...EVALUATION, hasScreenshots: true }} criteria={CRITERIA} />,
    );
    expect(screen.getByText("Captures non lues par le Praticien.")).toBeInTheDocument();
  });

  it.each([
    ["read", "Dépôt lu par le Praticien."],
    ["unreadable", "Le dépôt n'a pas pu être lu : l'évaluation s'appuie sur ta description."],
    ["none", "Aucun dépôt fourni : l'évaluation s'appuie sur ta description."],
  ] as const)("says how the repository was read (%s)", (repoStatus, text) => {
    renderView({ ...EVALUATION, repoStatus });
    expect(screen.getByText(text)).toBeInTheDocument();
  });
});
