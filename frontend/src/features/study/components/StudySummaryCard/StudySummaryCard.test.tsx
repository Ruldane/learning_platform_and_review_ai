import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { StudySummaryView } from "../viewTypes";
import { StudySummaryCard } from "./StudySummaryCard";

const SUMMARY: StudySummaryView = {
  moduleTitle: "Bases de données",
  lessonTitle: "Les index en SQL",
  minutes: 95,
  summary: "Tu as compris pourquoi un index évite un parcours complet.",
  tasksDone: ["Lire la leçon sur les index", "Écrire trois requêtes"],
  flashcardsCreated: 3,
  skills: [
    { name: "SQL", level: "en_cours" },
    { name: "Index", level: "declare" },
  ],
};

describe("StudySummaryCard", () => {
  it("shows the summary and the time worked", () => {
    render(<StudySummaryCard summary={SUMMARY} />);
    expect(screen.getByRole("heading", { name: "Session terminée" })).toBeInTheDocument();
    expect(screen.getByText("Bases de données : Les index en SQL")).toBeInTheDocument();
    expect(screen.getByText(SUMMARY.summary)).toBeInTheDocument();
    expect(screen.getByText("1 h 35")).toBeInTheDocument();
  });

  it("lists the ticked tasks", () => {
    render(<StudySummaryCard summary={SUMMARY} />);
    const list = screen.getByRole("list", { name: "Tâches cochées" });
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(SUMMARY.tasksDone);
  });

  it("counts the flashcards created", () => {
    const { rerender } = render(<StudySummaryCard summary={SUMMARY} />);
    expect(screen.getByText("3 fiches créées pour tes révisions.")).toBeInTheDocument();
    rerender(<StudySummaryCard summary={{ ...SUMMARY, flashcardsCreated: 1 }} />);
    expect(screen.getByText("1 fiche créée pour tes révisions.")).toBeInTheDocument();
    rerender(<StudySummaryCard summary={{ ...SUMMARY, flashcardsCreated: 0 }} />);
    expect(screen.getByText("Aucune nouvelle fiche.")).toBeInTheDocument();
  });

  it("lists the updated skills with their level in words", () => {
    render(<StudySummaryCard summary={SUMMARY} />);
    const list = screen.getByRole("list", { name: "Acquis mis à jour" });
    const items = within(list).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("SQL");
    expect(items[0]).toHaveTextContent("En cours");
    expect(items[1]).toHaveTextContent("Déclaré");
  });

  it("says so when nothing was ticked or updated", () => {
    render(<StudySummaryCard summary={{ ...SUMMARY, tasksDone: [], skills: [] }} />);
    expect(screen.getByText("Aucune tâche cochée.")).toBeInTheDocument();
    expect(screen.getByText("Aucun acquis mis à jour.")).toBeInTheDocument();
  });
});
