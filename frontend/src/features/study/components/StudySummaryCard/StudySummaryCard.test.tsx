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
    { name: "SQL", level: "in_progress" },
    { name: "Index", level: "declared" },
  ],
};

describe("StudySummaryCard", () => {
  it("shows the summary and the time worked", () => {
    render(<StudySummaryCard summary={SUMMARY} />);
    expect(screen.getByRole("heading", { name: "Session complete" })).toBeInTheDocument();
    expect(screen.getByText("Bases de données: Les index en SQL")).toBeInTheDocument();
    expect(screen.getByText(SUMMARY.summary)).toBeInTheDocument();
    expect(screen.getByText("1 h 35")).toBeInTheDocument();
  });

  it("lists the ticked tasks", () => {
    render(<StudySummaryCard summary={SUMMARY} />);
    const list = screen.getByRole("list", { name: "Tasks checked" });
    expect(
      within(list)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(SUMMARY.tasksDone);
  });

  it("counts the flashcards created", () => {
    const { rerender } = render(<StudySummaryCard summary={SUMMARY} />);
    expect(screen.getByText("3 cards created for your reviews.")).toBeInTheDocument();
    rerender(<StudySummaryCard summary={{ ...SUMMARY, flashcardsCreated: 1 }} />);
    expect(screen.getByText("1 card created for your reviews.")).toBeInTheDocument();
    rerender(<StudySummaryCard summary={{ ...SUMMARY, flashcardsCreated: 0 }} />);
    expect(screen.getByText("No new cards.")).toBeInTheDocument();
  });

  it("lists the updated skills with their level in words", () => {
    render(<StudySummaryCard summary={SUMMARY} />);
    const list = screen.getByRole("list", { name: "Skills updated" });
    const items = within(list).getAllByRole("listitem");
    expect(items[0]).toHaveTextContent("SQL");
    expect(items[0]).toHaveTextContent("In progress");
    expect(items[1]).toHaveTextContent("Declared");
  });

  it("says so when nothing was ticked or updated", () => {
    render(<StudySummaryCard summary={{ ...SUMMARY, tasksDone: [], skills: [] }} />);
    expect(screen.getByText("No tasks checked.")).toBeInTheDocument();
    expect(screen.getByText("No skills updated.")).toBeInTheDocument();
  });
});
