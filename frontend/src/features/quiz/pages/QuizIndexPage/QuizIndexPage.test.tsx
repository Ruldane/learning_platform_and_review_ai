import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router";
import { describe, expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { apiError, recordPosts } from "@/test/councilHarness";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { QuizIndexPage } from "./QuizIndexPage";

const program = { id: "p1", goal_id: "g1", title: "Backend", status: "validated", weeks: 8 };

const row = (over: Record<string, unknown> = {}) => ({
  module_id: "m1",
  module_title: "API REST",
  week_rank: 1,
  quiz_id: null,
  status: null,
  best_score: null,
  retry_on: null,
  ...over,
});

type Reply = () => Response | Promise<Response>;

function setup(options: { programs?: unknown[] | Reply; quizzes?: unknown[] | Reply } = {}) {
  const answer = (value: unknown[] | Reply | undefined, fallback: unknown[]) =>
    typeof value === "function" ? value() : HttpResponse.json(value ?? fallback);
  server.use(
    http.get(`${API}/programs`, () => answer(options.programs, [program])),
    http.get(`${API}/programs/p1/quizzes`, () => answer(options.quizzes, [row()])),
  );
  const router = createMemoryRouter(
    [
      { path: "/etudier/quiz", element: <QuizIndexPage pollMs={5} /> },
      { path: "/etudier/quiz/:quizId", element: <p>Page du quiz</p> },
      { path: "/apprendre/conseil", element: <p>Conseil</p> },
    ],
    { initialEntries: ["/etudier/quiz"] },
  );
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { router, user: userEvent.setup() };
}

describe("QuizIndexPage", () => {
  it("lists modules with best score and prepare action", async () => {
    setup({
      quizzes: [
        row(),
        row({
          module_id: "m2",
          module_title: "SQL",
          week_rank: 2,
          quiz_id: "z2",
          status: "ready",
          best_score: 85,
        }),
      ],
    });
    expect(
      await screen.findByRole("button", { name: "Préparer le quiz : API REST" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Meilleur score : 85 %")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refaire le quiz : SQL" })).toBeInTheDocument();
  });

  it("prepares a quiz once, then opens its page", async () => {
    const posts = recordPosts("/modules/m1/quiz", 202, {
      quiz_id: "z1",
      session_id: "s1",
      status: "generating",
    });
    const { router, user } = setup();
    await user.dblClick(await screen.findByRole("button", { name: "Préparer le quiz : API REST" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/etudier/quiz/z1"));
    expect(posts).toHaveLength(1);
  });

  it("opens a ready quiz", async () => {
    const { router, user } = setup({ quizzes: [row({ quiz_id: "z9", status: "ready" })] });
    await user.click(await screen.findByRole("button", { name: "Passer le quiz : API REST" }));
    expect(router.state.location.pathname).toBe("/etudier/quiz/z9");
  });

  it("shows a refused preparation inline and keeps the button", async () => {
    recordPosts("/modules/m1/quiz", 409, apiError("lesson_not_ready", "La leçon n'est pas prête."));
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Préparer le quiz : API REST" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La leçon n'est pas prête.");
    expect(screen.getByRole("button", { name: "Préparer le quiz : API REST" })).toBeEnabled();
  });

  it("reads the list again while a quiz is being prepared", async () => {
    let reads = 0;
    setup({
      quizzes: () => {
        reads += 1;
        return HttpResponse.json([
          reads < 3
            ? row({ quiz_id: "z1", status: "generating" })
            : row({ quiz_id: "z1", status: "ready" }),
        ]);
      },
    });
    expect(await screen.findByText("Quiz en préparation…")).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "Passer le quiz : API REST" }),
    ).toBeInTheDocument();
  });

  it("has an empty state with an action when there is no program", async () => {
    const { router, user } = setup({ programs: [] });
    expect(
      await screen.findByRole("heading", { name: "Pas encore de programme" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Aller au Conseil" }));
    expect(router.state.location.pathname).toBe("/apprendre/conseil");
  });

  it("has an empty state when the program has no module", async () => {
    setup({ quizzes: [] });
    expect(
      await screen.findByRole("heading", { name: "Aucun quiz pour le moment" }),
    ).toBeInTheDocument();
  });

  it("announces the loading", () => {
    setup({ programs: () => new Promise<Response>(() => {}) });
    expect(screen.getByRole("status")).toHaveTextContent("Chargement des quiz…");
  });

  it("shows an error with a retry button", async () => {
    let calls = 0;
    const { user } = setup({
      quizzes: () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(apiError("boom", "Panne du serveur."), { status: 500 })
          : HttpResponse.json([row()]);
      },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(
      await screen.findByRole("button", { name: "Préparer le quiz : API REST" }),
    ).toBeInTheDocument();
  });
});
