import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { API } from "@/test/councilApi";
import { apiError, recordPosts } from "@/test/councilHarness";
import { createQueryWrapper } from "@/test/queryWrapper";
import { attemptOut, firstOrder, quizApi, quizOut, secondOrder } from "@/test/quizApi";
import { server } from "@/test/server";
import { GRADE_POLL_MS, GRADE_POLLS } from "../../hooks/useAttempt";
import { PREPARE_POLL_MS, PREPARE_POLLS } from "../../hooks/useQuiz";
import { QuizPage } from "./QuizPage";

const TODAY = new Date(2026, 10, 17, 12);

/** `realPolling` : la page relit aux cadences réelles (tests sous faux minuteurs). */
function setup(api: Parameters<typeof quizApi>[0] = {}, realPolling = false) {
  const quiz = quizApi(api);
  server.use(...quiz.handlers);
  const page = realPolling ? <QuizPage /> : <QuizPage preparePollMs={5} gradePollMs={5} />;
  const router = createMemoryRouter(
    [
      { path: "/etudier/quiz/:quizId", element: page },
      { path: "/etudier/quiz", element: <p>Liste des quiz</p> },
    ],
    { initialEntries: ["/etudier/quiz/z1"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  const user = userEvent.setup(realPolling ? { advanceTimers: vi.advanceTimersByTime } : {});
  return { state: quiz.state, router, user };
}

const started = { attempt_id: "a1", session_id: "s9" };

async function answerAndSend(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("radio", { name: "GET" }));
  await user.type(
    screen.getByRole("textbox", { name: "Ta réponse à la question 2" }),
    " Remplace ",
  );
  await user.click(screen.getByRole("button", { name: "Envoyer" }));
}

describe("QuizPage", () => {
  // Le jour du poste est figé : les dates de nouvel essai des doublures (19 novembre) sont à venir.
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"], shouldAdvanceTime: true });
    vi.setSystemTime(TODAY);
  });
  afterEach(() => vi.useRealTimers());

  it("prepares then takes a quiz and shows the result", async () => {
    const posts = recordPosts("/quizzes/z1/attempts", 202, started);
    const { user } = setup({
      quizzes: [quizOut({ status: "generating" }), quizOut({ status: "generating" }), quizOut()],
      attempts: [attemptOut({ status: "grading", score: null, passed: null }), attemptOut()],
    });
    expect(await screen.findByText(/Le quiz se prépare/)).toBeInTheDocument();
    await answerAndSend(user);
    expect(await screen.findByText("Correction en cours…")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Résultat du quiz" })).toBeInTheDocument();
    expect(screen.getByText("50 %")).toBeInTheDocument();
    expect(screen.getByText("Que fait PUT ?")).toBeInTheDocument();
    expect(posts).toEqual([
      {
        elapsed_ms: expect.any(Number),
        answers: [
          { question_id: "q1", choice: 0, text: "" },
          { question_id: "q2", choice: null, text: "Remplace" },
        ],
      },
    ]);
  });

  it("reads the quiz again after the grade and joins results to the questions as sent", async () => {
    recordPosts("/quizzes/z1/attempts", 202, started);
    const { user, state } = setup({
      quizzes: [quizOut(), quizOut({ questions: secondOrder })],
      // Nouvel essai possible dès aujourd'hui : « Refaire le quiz » est proposé.
      attempts: [
        attemptOut({ followup: { revision_tasks: [], retry_on: "2026-11-17", unplaced: 0 } }),
      ],
    });
    await answerAndSend(user);
    expect(await screen.findByRole("heading", { name: "Résultat du quiz" })).toBeInTheDocument();
    await waitFor(() => expect(state.quizReads).toBeGreaterThanOrEqual(2));
    // Les rangs du résultat sont ceux de l'envoi (PUT était la question 2), pas ceux du prochain essai.
    const second = screen
      .getAllByRole("listitem")
      .find((item) => /Que fait PUT/.test(item.textContent ?? ""));
    expect(second).toHaveTextContent("Question 2");
    // Le prochain essai montre l'ordre mélangé : la réponse courte passe en premier.
    await user.click(await screen.findByRole("button", { name: "Refaire le quiz" }));
    const fields = await screen.findAllByRole("textbox");
    expect(fields[0]).toHaveAccessibleName("Ta réponse à la question 1");
    expect(screen.getByRole("radio", { name: "POST" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { checked: true })).not.toBeInTheDocument();
  });

  it("shows the retry_too_soon date", async () => {
    recordPosts(
      "/quizzes/z1/attempts",
      409,
      apiError("retry_too_soon", "Trop tôt.", { retry_on: "2026-11-19" }),
    );
    const { user } = setup();
    await answerAndSend(user);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Nouvel essai possible à partir du jeudi 19 novembre.",
    );
    expect(screen.getByRole("button", { name: "Envoyer" })).toBeEnabled();
  });

  it("keeps the result on screen when the quiz cannot be read again (E-I2)", async () => {
    recordPosts("/quizzes/z1/attempts", 202, started);
    let reads = 0;
    const { user } = setup({
      quizReply: () => {
        reads += 1;
        return reads === 1
          ? HttpResponse.json(quizOut())
          : HttpResponse.json(apiError("boom", "Panne du serveur."), { status: 500 });
      },
    });
    await answerAndSend(user);
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    expect(screen.getByRole("heading", { name: "Résultat du quiz" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Réessayer" })).toBeInTheDocument();
  });

  it("sends the answers once on a double click", async () => {
    const posts = recordPosts("/quizzes/z1/attempts", 202, started);
    const { user } = setup();
    await user.click(await screen.findByRole("radio", { name: "GET" }));
    await user.type(
      screen.getByRole("textbox", { name: "Ta réponse à la question 2" }),
      "Remplace",
    );
    await user.dblClick(screen.getByRole("button", { name: "Envoyer" }));
    await screen.findByRole("heading", { name: "Résultat du quiz" });
    expect(posts).toHaveLength(1);
  });

  it("resends the same answers after a failed grading", async () => {
    const { user } = setup({
      attempts: [attemptOut({ status: "failed", score: null, passed: null, results: [] })],
    });
    const posts: unknown[] = [];
    server.use(
      http.post(`${API}/quizzes/z1/attempts`, async ({ request }) => {
        posts.push(await request.json());
        return HttpResponse.json(
          { attempt_id: posts.length === 1 ? "a1" : "a2", session_id: "s9" },
          { status: 202 },
        );
      }),
    );
    await answerAndSend(user);
    expect(await screen.findByText("La correction a échoué")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Renvoyer mes réponses" }));
    expect(await screen.findByRole("heading", { name: "Résultat du quiz" })).toBeInTheDocument();
    expect(posts).toHaveLength(2);
    expect(posts[1]).toEqual(posts[0]);
  });

  it("resends once on a double click (revue finale 5, E-m5)", async () => {
    const { user } = setup({
      attempts: [attemptOut({ status: "failed", score: null, passed: null, results: [] })],
    });
    const posts: unknown[] = [];
    server.use(
      http.post(`${API}/quizzes/z1/attempts`, async ({ request }) => {
        posts.push(await request.json());
        return HttpResponse.json(
          { attempt_id: posts.length === 1 ? "a1" : "a2", session_id: "s9" },
          { status: 202 },
        );
      }),
    );
    await answerAndSend(user);
    await user.dblClick(await screen.findByRole("button", { name: "Renvoyer mes réponses" }));
    expect(await screen.findByRole("heading", { name: "Résultat du quiz" })).toBeInTheDocument();
    expect(posts).toHaveLength(2);
  });

  it("takes up a grading that was already running after a reload", async () => {
    const { state } = setup({
      quizzes: [
        quizOut({
          attempts: [
            { id: "a1", status: "grading", score: null, created_at: "2026-11-17T10:00:00Z" },
          ],
        }),
      ],
      attempts: [attemptOut({ status: "grading", score: null, passed: null }), attemptOut()],
    });
    expect(await screen.findByText("Correction en cours…")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Résultat du quiz" })).toBeInTheDocument();
    expect(state.attemptReads).toBeGreaterThanOrEqual(2);
  });

  // Cadences réelles sous faux minuteurs : l'horloge saute les relectures, aucune attente réelle
  // (sous charge, 40 ou 90 relectures en vrai temps dépassaient le délai de `findBy`). Les
  // `clear*` sont faussés aussi : sinon TanStack ne peut plus arrêter un intervalle faux, et les
  // relectures s'additionnent.
  function fakePollingClock() {
    vi.useFakeTimers({
      toFake: ["Date", "setTimeout", "clearTimeout", "setInterval", "clearInterval"],
      shouldAdvanceTime: true,
    });
    vi.setSystemTime(TODAY);
  }

  /** `polls` relectures, une cadence à la fois : d'un seul saut, les tops de l'intervalle
   * tomberaient pendant la première lecture en cours, et TanStack n'en ferait qu'une. */
  async function pollFor(pollMs: number, polls: number) {
    for (let i = 0; i < polls; i += 1) await act(() => vi.advanceTimersByTimeAsync(pollMs));
  }

  it("says when the preparation takes too long and waits again on request", async () => {
    fakePollingClock();
    const generating = quizOut({ status: "generating" });
    const { user } = setup(
      { quizzes: [...Array.from({ length: PREPARE_POLLS + 2 }, () => generating), quizOut()] },
      true,
    );
    await pollFor(PREPARE_POLL_MS, PREPARE_POLLS + 2);
    expect(screen.getByText(/La préparation prend plus de temps/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continuer d'attendre" }));
    await pollFor(PREPARE_POLL_MS, 3);
    expect(await screen.findByRole("form", { name: "Quiz" })).toBeInTheDocument();
  });

  it("says when the grading takes too long and reads the grade again on request", async () => {
    fakePollingClock();
    recordPosts("/quizzes/z1/attempts", 202, started);
    const grading = attemptOut({ status: "grading", score: null, passed: null });
    const { user } = setup(
      { attempts: [...Array.from({ length: GRADE_POLLS + 2 }, () => grading), attemptOut()] },
      true,
    );
    await answerAndSend(user);
    await pollFor(GRADE_POLL_MS, GRADE_POLLS + 2);
    expect(screen.getByText(/La correction prend plus de temps/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Relire la note" }));
    await pollFor(GRADE_POLL_MS, 3);
    expect(await screen.findByRole("heading", { name: "Résultat du quiz" })).toBeInTheDocument();
  });

  it("relaunches a failed preparation", async () => {
    const posts = recordPosts("/modules/m1/quiz", 202, {
      quiz_id: "z1",
      session_id: "s2",
      status: "generating",
    });
    const { user } = setup({
      quizzes: [
        quizOut({ status: "failed", questions: [], failure_reason: "Le modèle n'a pas répondu." }),
        quizOut(),
      ],
    });
    expect(await screen.findByText("La préparation du quiz a échoué")).toBeInTheDocument();
    expect(screen.getByText("Le modèle n'a pas répondu.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Relancer la préparation" }));
    expect(await screen.findByRole("form", { name: "Quiz" })).toBeInTheDocument();
    expect(posts).toHaveLength(1);
  });

  it("has an empty state for an unknown quiz", async () => {
    const { user, router } = setup({
      quizReply: () =>
        HttpResponse.json(apiError("quiz_not_found", "Quiz introuvable."), { status: 404 }),
    });
    expect(await screen.findByRole("heading", { name: "Quiz introuvable" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tous les quiz" }));
    expect(router.state.location.pathname).toBe("/etudier/quiz");
  });

  it("announces the loading, then shows an error with a retry button", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/quizzes/z1`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(apiError("boom", "Panne du serveur."), { status: 500 })
          : HttpResponse.json(quizOut());
      }),
    );
    const router = createMemoryRouter([{ path: "/etudier/quiz/:quizId", element: <QuizPage /> }], {
      initialEntries: ["/etudier/quiz/z1"],
    });
    render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
    expect(screen.getByRole("status")).toHaveTextContent("Chargement du quiz…");
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("form", { name: "Quiz" })).toBeInTheDocument();
    expect(firstOrder).toHaveLength(2);
  });
});
