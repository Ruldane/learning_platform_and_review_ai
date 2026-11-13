import { describe, expect, it } from "vitest";
import type { QuestionView } from "./components/viewTypes";
import { dayOf, percent, toAttemptResultView, toQuizSummaryView } from "./toView";
import type { AttemptOut } from "./types";

const questions: QuestionView[] = [
  {
    id: "q2",
    rank: 1,
    type: "qcm",
    prompt: "Quel verbe lit ?",
    code: null,
    choices: ["GET", "POST"],
  },
  { id: "q1", rank: 2, type: "short", prompt: "Que fait PUT ?", code: null, choices: [] },
];

const attempt: AttemptOut = {
  id: "a1",
  status: "graded",
  score: 62,
  passed: false,
  results: [
    {
      question_id: "q1",
      points: 0.5,
      correct_answer: "Remplace.",
      explanation: "PUT remplace.",
      feedback: "Presque.",
    },
    { question_id: "q2", points: 1, correct_answer: "GET", explanation: "GET lit.", feedback: "" },
  ],
  followup: { revision_tasks: ["Réviser : REST"], retry_on: "2026-11-19", unplaced: 1 },
};

describe("toView", () => {
  it("joins each result to the statement it answered, at the rank shown", () => {
    const view = toAttemptResultView(attempt, questions);
    expect(view.score).toBe(62);
    expect(view.passed).toBe(false);
    expect(view.results[0]).toMatchObject({
      questionId: "q1",
      rank: 2,
      prompt: "Que fait PUT ?",
      points: 0.5,
    });
    expect(view.results[1]).toMatchObject({
      questionId: "q2",
      rank: 1,
      prompt: "Quel verbe lit ?",
    });
    expect(view.followup).toEqual({
      revisionTasks: ["Réviser : REST"],
      retryOn: "2026-11-19",
      unplaced: 1,
    });
  });

  it("has no follow-up when the quiz is passed and keeps a result without its statement", () => {
    const view = toAttemptResultView({ ...attempt, passed: true, score: 85, followup: null }, []);
    expect(view.passed).toBe(true);
    expect(view.followup).toBeNull();
    expect(view.results[0]).toMatchObject({ rank: 1, prompt: "" });
  });

  it("keeps scores to whole percents between 0 and 100", () => {
    expect(percent(84.6)).toBe(85);
    expect(percent(140)).toBe(100);
    expect(percent(-3)).toBe(0);
  });

  it("reads a day as YYYY-MM-DD and refuses anything else", () => {
    expect(dayOf("2026-11-19T00:00:00")).toBe("2026-11-19");
    expect(dayOf("demain")).toBeNull();
    expect(dayOf(null)).toBeNull();
  });

  it("maps a list row with an integer best score", () => {
    expect(
      toQuizSummaryView({
        module_id: "m1",
        module_title: "REST",
        week_rank: 2,
        quiz_id: "z1",
        status: "ready",
        best_score: 75,
        retry_on: null,
      }),
    ).toEqual({
      moduleId: "m1",
      moduleTitle: "REST",
      weekRank: 2,
      quizId: "z1",
      status: "ready",
      bestScore: 75,
      retryOn: null,
    });
  });
});
