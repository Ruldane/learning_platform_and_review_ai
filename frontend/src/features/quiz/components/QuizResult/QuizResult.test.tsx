import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { AttemptResultView, FollowupView } from "../viewTypes";
import { QuizResult } from "./QuizResult";

const RESULTS = [
  {
    questionId: "q1",
    rank: 1,
    prompt: "Quel index accélère une recherche par égalité ?",
    points: 1,
    correctAnswer: "Hash",
    explanation: "Un index de hachage trouve une clé en temps constant.",
    feedback: "",
  },
  {
    questionId: "q2",
    rank: 2,
    prompt: "Que fait EXPLAIN ?",
    points: 0.5,
    correctAnswer: "Il montre le plan d'exécution.",
    explanation: "EXPLAIN décrit le plan choisi, sans exécuter la requête.",
    feedback: "Tu as vu le plan mais pas qu'il n'exécute rien.",
  },
  {
    questionId: "q3",
    rank: 3,
    prompt: "Explique ce qu'est une jointure.",
    points: 0,
    correctAnswer: "Une jointure relie des lignes de deux tables.",
    explanation: "Elle associe les lignes selon une condition commune.",
    feedback: "Tu parles de tri, pas de liaison entre tables.",
  },
];

const FOLLOWUP: FollowupView = {
  revisionTasks: ["Réviser : SQL", "Refaire le quiz : Bases de données"],
  retryOn: "2026-11-17",
  unplaced: 0,
};

const PASSED: AttemptResultView = {
  score: 85,
  passed: true,
  results: RESULTS.map((r) => ({ ...r, points: 1 })),
  followup: null,
};

const FAILED: AttemptResultView = {
  score: 50,
  passed: false,
  results: RESULTS,
  followup: FOLLOWUP,
};

const detailItems = () =>
  within(screen.getByRole("list", { name: "Breakdown by question" })).getAllByRole("listitem");

function detail(rank: number): HTMLElement {
  const item = detailItems()[rank - 1];
  if (item === undefined) throw new Error(`no detail for question ${rank}`);
  return item;
}

describe("QuizResult", () => {
  it("validates the skill at 80 percent", () => {
    render(<QuizResult result={{ ...PASSED, score: 80 }} />);
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("Skill validated")).toBeInTheDocument();
    expect(screen.queryByText(/not validated yet/)).not.toBeInTheDocument();
  });

  it("says what is missing below 80 percent", () => {
    render(<QuizResult result={FAILED} />);
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.queryByText("Skill validated")).not.toBeInTheDocument();
    expect(screen.getByText(/you need 80% to validate it/)).toBeInTheDocument();
  });

  it("totals the points", () => {
    render(<QuizResult result={FAILED} />);
    expect(screen.getByText("Points: 1.5 of 3")).toBeInTheDocument();
  });

  it("shows explanation for each error", () => {
    render(<QuizResult result={FAILED} />);
    expect(detailItems()).toHaveLength(3);
    expect(detail(2)).toHaveTextContent("Partly correct");
    expect(detail(2)).toHaveTextContent("0.5 pt");
    expect(detail(2)).toHaveTextContent("Il montre le plan d'exécution.");
    expect(detail(2)).toHaveTextContent("EXPLAIN décrit le plan choisi");
    expect(detail(2)).toHaveTextContent("Tu as vu le plan mais pas qu'il n'exécute rien.");
    expect(detail(3)).toHaveTextContent("Wrong");
    expect(detail(3)).toHaveTextContent("0 pt");
    expect(detail(3)).toHaveTextContent("Une jointure relie des lignes de deux tables.");
    expect(detail(3)).toHaveTextContent("Elle associe les lignes selon une condition commune.");
    expect(detail(3)).toHaveTextContent("Tu parles de tri, pas de liaison entre tables.");
    expect(detail(2).querySelector("details")).toBeNull();
  });

  it("keeps the details of a right answer one click away", () => {
    render(<QuizResult result={FAILED} />);
    const first = detail(1);
    expect(first).toHaveTextContent("Correct");
    const details = first.querySelector("details");
    expect(details).not.toBeNull();
    expect(details).not.toHaveAttribute("open");
    expect(details).toHaveTextContent("Hash");
    expect(details).toHaveTextContent("Un index de hachage trouve une clé en temps constant.");
  });

  it("omits the empty feedback of a multiple choice question", () => {
    render(<QuizResult result={FAILED} />);
    expect(detail(1)).not.toHaveTextContent("Feedback on your answer");
  });

  it("shows retry date and unplaced warning", () => {
    render(<QuizResult result={{ ...FAILED, followup: { ...FOLLOWUP, unplaced: 1 } }} />);
    expect(
      screen.getByRole("list", { name: "Reviews added to your schedule" }),
    ).toHaveTextContent("Réviser : SQL");
    expect(
      screen.getByText("You can try again from Tuesday 17 November."),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "1 review didn’t fit in your budget",
    );
  });

  it("pluralises the unplaced warning and hides it when everything is placed", () => {
    const { rerender } = render(
      <QuizResult result={{ ...FAILED, followup: { ...FOLLOWUP, unplaced: 2 } }} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("2 reviews didn’t fit in your budget");
    rerender(<QuizResult result={FAILED} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows no follow-up after a pass", () => {
    render(<QuizResult result={PASSED} />);
    expect(screen.queryByText(/You can try again/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("list", { name: "Reviews added to your schedule" }),
    ).not.toBeInTheDocument();
  });
});
