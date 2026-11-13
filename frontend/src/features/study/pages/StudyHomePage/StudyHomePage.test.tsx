import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { ReactElement } from "react";
import { createMemoryRouter, RouterProvider, type InitialEntry } from "react-router";
import { describe, expect, it, vi } from "vitest";
import { API } from "@/test/councilApi";
import { apiError, recordPosts } from "@/test/councilHarness";
import { createQueryWrapper } from "@/test/queryWrapper";
import { server } from "@/test/server";
import { summaryOut } from "@/test/studyApi";
import { StudyHomePage } from "./StudyHomePage";

const started = { study_session_id: "st1", session_id: "s1", lesson_id: "l1" };

type Summary = Record<string, unknown> | (() => Response | Promise<Response>);

function setup(summary: Summary = summaryOut(), entry: InitialEntry = "/etudier/session") {
  server.use(
    http.get(`${API}/study-sessions/summary`, () =>
      typeof summary === "function" ? summary() : HttpResponse.json(summary),
    ),
    http.get(`${API}/lessons/l1`, () => HttpResponse.json({ id: "l1", title: "Les API REST" })),
  );
  const routes: { path: string; element: ReactElement }[] = [
    { path: "/etudier/session", element: <StudyHomePage /> },
    { path: "/etudier/session/:studyId", element: <p>Session ouverte</p> },
    { path: "/apprendre/lecons", element: <p>Liste des leçons</p> },
  ];
  const router = createMemoryRouter(routes, { initialEntries: [entry] });
  render(<RouterProvider router={router} />, { wrapper: createQueryWrapper() });
  return { router, user: userEvent.setup() };
}

describe("StudyHomePage", () => {
  it("starts the block and opens the session", async () => {
    const posts = recordPosts("/study-sessions", 202, started);
    const { router, user } = setup();
    expect(await screen.findByRole("heading", { name: "Les API REST" })).toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: /Feynman/ }));
    await user.click(screen.getByRole("button", { name: "Commencer mon bloc" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/etudier/session/st1"));
    expect(posts).toEqual([{ mode: "feynman" }]);
  });

  it("starts only once on a double click", async () => {
    const posts = recordPosts("/study-sessions", 202, started);
    const { user } = setup();
    const button = await screen.findByRole("button", { name: "Commencer mon bloc" });
    await user.dblClick(button);
    await screen.findByText("Session ouverte");
    expect(posts).toHaveLength(1);
  });

  it("resumes the open session", async () => {
    const posts = recordPosts("/study-sessions", 202, started);
    const { router, user } = setup(summaryOut({ open_session_id: "st9" }));
    await user.click(await screen.findByRole("button", { name: "Reprendre ma session" }));
    expect(router.state.location.pathname).toBe("/etudier/session/st9");
    expect(screen.queryByRole("button", { name: "Commencer mon bloc" })).not.toBeInTheDocument();
    expect(posts).toHaveLength(0);
  });

  it("goes to the open session instead of showing study_already_open", async () => {
    recordPosts(
      "/study-sessions",
      409,
      apiError("study_already_open", "Une session est déjà ouverte.", { study_session_id: "st9" }),
    );
    const { router, user } = setup();
    await user.click(await screen.findByRole("button", { name: "Commencer mon bloc" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/etudier/session/st9"));
  });

  it("offers to choose a lesson on no_block_today", async () => {
    recordPosts("/study-sessions", 404, apiError("no_block_today", "Pas de bloc aujourd'hui."));
    const { router, user } = setup();
    await user.click(await screen.findByRole("button", { name: "Commencer mon bloc" }));
    expect(
      await screen.findByRole("heading", { name: "Aucun bloc prévu aujourd'hui" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choisir une leçon" }));
    expect(router.state.location.pathname).toBe("/apprendre/lecons");
  });

  it("shows an empty state with an action when there is no block and no session", async () => {
    const { user, router } = setup(summaryOut({ block: null }));
    expect(
      await screen.findByRole("heading", { name: "Aucun bloc prévu aujourd'hui" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choisir une leçon" }));
    expect(router.state.location.pathname).toBe("/apprendre/lecons");
  });

  it("shows another start error inline and keeps the button", async () => {
    recordPosts("/study-sessions", 409, apiError("lesson_not_ready", "La leçon n'est pas prête."));
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Commencer mon bloc" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La leçon n'est pas prête.");
    expect(screen.getByRole("button", { name: "Commencer mon bloc" })).toBeEnabled();
  });

  it("preselects the lesson from ?lecon", async () => {
    const posts = recordPosts("/study-sessions", 202, started);
    const { router, user } = setup(summaryOut(), "/etudier/session?lecon=l1");
    expect(await screen.findByRole("heading", { name: "Les API REST" })).toBeInTheDocument();
    expect(screen.queryByText("Ton bloc du jour")).not.toBeInTheDocument();
    expect(screen.queryByText("Ta question pour le tuteur")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Étudier cette leçon" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/etudier/session/st1"));
    expect(posts).toEqual([{ lesson_id: "l1", mode: "socratic" }]);
  });

  it("asks the tutor about a passage in direct mode, cut at 2000 characters", async () => {
    const posts = recordPosts("/study-sessions", 202, started);
    const passage = "x".repeat(2500);
    const { user } = setup(summaryOut(), {
      pathname: "/etudier/session",
      state: { lessonId: "l1", question: passage },
    } as InitialEntry);
    expect(await screen.findByText("Ta question pour le tuteur")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Direct/ })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Poser ma question au tuteur" }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toEqual({ lesson_id: "l1", mode: "direct", question: "x".repeat(2000) });
  });

  it("keeps the open session within reach when a lesson is chosen", async () => {
    const { router, user } = setup(
      summaryOut({ open_session_id: "st9" }),
      "/etudier/session?lecon=l1",
    );
    await screen.findByRole("heading", { name: "Les API REST" });
    await user.click(screen.getByRole("button", { name: "Reprendre ma session" }));
    expect(router.state.location.pathname).toBe("/etudier/session/st9");
  });

  it("announces the loading", () => {
    setup(() => new Promise<Response>(() => {}));
    expect(screen.getByRole("status")).toHaveTextContent("Chargement de ton bloc du jour…");
  });

  it("shows an error with a retry button", async () => {
    let calls = 0;
    const { user } = setup(() => {
      calls += 1;
      return calls === 1
        ? HttpResponse.json(apiError("boom", "Panne du serveur."), { status: 500 })
        : HttpResponse.json(summaryOut());
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Panne du serveur.");
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("button", { name: "Commencer mon bloc" })).toBeInTheDocument();
  });

  it("never opens a browser dialog", async () => {
    const dialog = vi.spyOn(window, "confirm");
    recordPosts("/study-sessions", 202, started);
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Commencer mon bloc" }));
    expect(dialog).not.toHaveBeenCalled();
  });
});
