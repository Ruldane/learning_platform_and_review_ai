import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { EvaluationDataView } from "../viewTypes";
import { EvaluationView } from "./EvaluationView";

const EVALUATION: EvaluationDataView = {
  verdict: "to_redo",
  feedback: "Le total n'est pas testé.",
  repoStatus: "read",
  hasScreenshots: false,
  results: [
    { index: 1, criterion: "Ventes agrégées par mois", met: true, comment: "Correct." },
    { index: 2, criterion: "Un test vérifie le total", met: false, comment: "Aucun test." },
  ],
};

describe("EvaluationView", () => {
  it("writes the verdict, the feedback and every criterion", () => {
    render(<EvaluationView evaluation={EVALUATION} />);
    expect(
      screen.getByRole("heading", { level: 2, name: "Évaluation du Praticien" }),
    ).toBeVisible();
    expect(screen.getByText("Projet à refaire")).toBeInTheDocument();
    expect(screen.getByText("Le total n'est pas testé.")).toBeInTheDocument();
    expect(screen.getByText("Ventes agrégées par mois")).toBeInTheDocument();
    expect(screen.getByText("Atteint")).toBeInTheDocument();
    expect(screen.getByText("Non atteint")).toBeInTheDocument();
  });

  it("writes a validated verdict", () => {
    render(<EvaluationView evaluation={{ ...EVALUATION, verdict: "validated" }} />);
    expect(screen.getByText("Projet validé")).toBeInTheDocument();
  });

  it("says that the screenshots were not read when there are some", () => {
    const { rerender } = render(<EvaluationView evaluation={EVALUATION} />);
    expect(screen.queryByText("Captures non lues par le Praticien.")).toBeNull();
    rerender(<EvaluationView evaluation={{ ...EVALUATION, hasScreenshots: true }} />);
    expect(screen.getByText("Captures non lues par le Praticien.")).toBeInTheDocument();
  });

  it.each([
    ["read", "Dépôt lu par le Praticien."],
    ["unreadable", "Le dépôt n'a pas pu être lu : l'évaluation s'appuie sur ta description."],
    ["none", "Aucun dépôt fourni : l'évaluation s'appuie sur ta description."],
  ] as const)("says how the repository was read (%s)", (repoStatus, text) => {
    render(<EvaluationView evaluation={{ ...EVALUATION, repoStatus }} />);
    expect(screen.getByText(text)).toBeInTheDocument();
  });
});
