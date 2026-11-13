import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { recordPosts } from "@/test/councilHarness";
import { createQueryWrapper } from "@/test/queryWrapper";
import { quizApi, quizOut } from "@/test/quizApi";
import { server } from "@/test/server";
import { QuizPage } from "./QuizPage";

function setup(api: Parameters<typeof quizApi>[0] = {}) {
  const quiz = quizApi(api);
  server.use(...quiz.handlers);
  const router = createMemoryRouter(
    [{ path: "/etudier/quiz/:quizId", element: <QuizPage preparePollMs={5} gradePollMs={5} /> }],
    { initialEntries: ["/etudier/quiz/z1"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { user: userEvent.setup() };
}

const started = { attempt_id: "a1", session_id: "s9" };

async function answerAndSend(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("radio", { name: "GET" }));
  await user.type(screen.getByRole("textbox", { name: "Ta réponse à la question 2" }), "Remplace");
  await user.click(screen.getByRole("button", { name: "Envoyer" }));
}

/** Revue finale 5 (E-I3) : pas de nouvel essai proposé avant sa date (F9, J+2). */
describe("QuizPage: date of the next try", () => {
  // Le jour du poste est figé : le nouvel essai des doublures (19 novembre) est à venir.
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"], shouldAdvanceTime: true });
    vi.setSystemTime(new Date(2026, 10, 17, 12));
  });
  afterEach(() => vi.useRealTimers());

  it("hides Refaire le quiz until the date of the next try (revue finale 5, E-I3)", async () => {
    recordPosts("/quizzes/z1/attempts", 202, started);
    const { user } = setup();
    await answerAndSend(user);
    expect(await screen.findByRole("heading", { name: "Résultat du quiz" })).toBeInTheDocument();
    expect(
      screen.getByText("Nouvel essai possible à partir du jeudi 19 novembre."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Refaire le quiz" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Voir tous les quiz" })).toBeInTheDocument();
  });

  it("shows the date instead of the form while the next try is not open", async () => {
    setup({
      quizzes: [
        quizOut({
          attempts: [
            { id: "a0", status: "graded", score: 90, created_at: "2026-11-10T10:00:00Z" },
            { id: "a1", status: "graded", score: 60, created_at: "2026-11-16T10:00:00Z" },
          ],
        }),
      ],
    });
    expect(
      await screen.findByText("Nouvel essai possible à partir du mercredi 18 novembre."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("form", { name: "Quiz" })).not.toBeInTheDocument();
  });

  it("shows the form again once the date of the next try has come", async () => {
    setup({
      quizzes: [
        quizOut({
          attempts: [{ id: "a1", status: "graded", score: 60, created_at: "2026-11-15T10:00:00Z" }],
        }),
      ],
    });
    expect(await screen.findByRole("form", { name: "Quiz" })).toBeInTheDocument();
    expect(screen.queryByText(/Nouvel essai possible/)).not.toBeInTheDocument();
  });
});
