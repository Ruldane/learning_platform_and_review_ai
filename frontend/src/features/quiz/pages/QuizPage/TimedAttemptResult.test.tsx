import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";
import type { AttemptResultView } from "../../components/viewTypes";
import { TimedAttemptResult } from "./TimedAttemptResult";

const result: AttemptResultView = {
  score: 67,
  passed: false,
  followup: null,
  results: Array.from({ length: 6 }, (_, index) => ({
    questionId: `q-${index}`,
    rank: index + 1,
    prompt: `Énoncé ${index}`,
    points: index === 3 || index === 4 ? 0 : 1,
    correctAnswer: "Utilise un index.",
    explanation: "Un index repère la ligne.",
    feedback: "",
  })),
};

describe("Focus pilot after grading", () => {
  it("offers a short review and returns to the original result", async () => {
    const timings = result.results.map(({ questionId: id }, index) => ({
      id,
      milliseconds: index < 3 ? 2_000 : 7_000,
    }));
    render(
      <MemoryRouter>
        <TimedAttemptResult result={result} timings={timings} refreshing={false} onBack={vi.fn()} />
      </MemoryRouter>,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Easier review" }));
    const review = screen.getByRole("complementary", { name: "Easier review" });
    expect(within(review).getByText("Énoncé 3")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Quiz result" })).toBeNull();
    await user.click(within(review).getByRole("button", { name: "Pick up where you left off" }));
    expect(screen.getByRole("heading", { name: "Quiz result" })).toBeVisible();
    expect(screen.getByText("67%")).toBeVisible();
  });
});
