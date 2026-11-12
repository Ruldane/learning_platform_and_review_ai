import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { QuizSummaryView } from "../viewTypes";
import { QuizList } from "./QuizList";

const READY: QuizSummaryView = {
  moduleId: "m1",
  moduleTitle: "Bases de données",
  weekRank: 1,
  quizId: "z1",
  status: "ready",
  bestScore: 85,
  retryOn: null,
};

const ITEMS: QuizSummaryView[] = [
  READY,
  {
    moduleId: "m2",
    moduleTitle: "API REST",
    weekRank: 2,
    quizId: null,
    status: null,
    bestScore: null,
    retryOn: null,
  },
  {
    moduleId: "m3",
    moduleTitle: "Tests",
    weekRank: 3,
    quizId: "z3",
    status: "generating",
    bestScore: null,
    retryOn: null,
  },
  {
    moduleId: "m4",
    moduleTitle: "Sécurité",
    weekRank: 4,
    quizId: "z4",
    status: "failed",
    bestScore: null,
    retryOn: null,
  },
  {
    moduleId: "m5",
    moduleTitle: "Docker",
    weekRank: 5,
    quizId: "z5",
    status: "ready",
    bestScore: 60,
    retryOn: "2026-11-17",
  },
];

function setup(props: Partial<Parameters<typeof QuizList>[0]> = {}) {
  const handlers = { onPrepare: vi.fn(), onOpen: vi.fn() };
  render(<QuizList items={ITEMS} {...handlers} {...props} />);
  return handlers;
}

const row = (title: string) => {
  const item = screen.getByText(title).closest("li");
  if (item === null) throw new Error(`no row for ${title}`);
  return item;
};

describe("QuizList", () => {
  it("lists modules with best score and prepare action", async () => {
    const { onPrepare, onOpen } = setup();
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
    expect(row("Bases de données")).toHaveTextContent("Semaine 1");
    expect(row("Bases de données")).toHaveTextContent("Meilleur score : 85 %");
    expect(row("API REST")).toHaveTextContent("Pas encore tenté");
    await userEvent.click(screen.getByRole("button", { name: "Préparer le quiz : API REST" }));
    expect(onPrepare).toHaveBeenCalledWith("m2");
    await userEvent.click(
      screen.getByRole("button", { name: "Refaire le quiz : Bases de données" }),
    );
    expect(onOpen).toHaveBeenCalledWith("z1");
  });

  it("opens a ready quiz that has no attempt yet", async () => {
    const { onOpen } = setup({
      items: [{ ...READY, bestScore: null }],
    });
    await userEvent.click(
      screen.getByRole("button", { name: "Passer le quiz : Bases de données" }),
    );
    expect(onOpen).toHaveBeenCalledWith("z1");
  });

  it("shows that a quiz is being prepared, without an action", () => {
    setup();
    expect(row("Tests")).toHaveTextContent("Quiz en préparation");
    expect(within(row("Tests")).queryByRole("button")).not.toBeInTheDocument();
  });

  it("offers to retry a failed preparation", async () => {
    const { onPrepare } = setup();
    expect(row("Sécurité")).toHaveTextContent("La préparation du quiz a échoué.");
    await userEvent.click(screen.getByRole("button", { name: "Réessayer : Sécurité" }));
    expect(onPrepare).toHaveBeenCalledWith("m4");
  });

  it("shows the date of the next try", () => {
    setup();
    expect(row("Docker")).toHaveTextContent("Nouvel essai à partir du mardi 17 novembre");
    expect(row("Docker")).toHaveTextContent("Meilleur score : 60 %");
  });

  it("disables the buttons while a module is being prepared", () => {
    setup({ pendingModuleId: "m2" });
    expect(screen.getByRole("button", { name: "Préparer le quiz : API REST" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Réessayer : Sécurité" })).toBeEnabled();
  });

  it("orders the modules by week", () => {
    setup({ items: [...ITEMS].reverse() });
    const titles = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(titles).toEqual(["Bases de données", "API REST", "Tests", "Sécurité", "Docker"]);
  });

  it("says there is nothing to test yet", () => {
    setup({ items: [] });
    expect(screen.getByText("Aucun quiz pour le moment")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });
});
