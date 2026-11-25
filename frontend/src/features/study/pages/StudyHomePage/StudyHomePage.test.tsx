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

function setup(summary: Summary = summaryOut(), entry: InitialEntry = "/study/session") {
  server.use(
    http.get(`${API}/study-sessions/summary`, () =>
      typeof summary === "function" ? summary() : HttpResponse.json(summary),
    ),
    http.get(`${API}/lessons/l1`, () => HttpResponse.json({ id: "l1", title: "Les API REST" })),
  );
  const routes: { path: string; element: ReactElement }[] = [
    { path: "/study/session", element: <StudyHomePage /> },
    { path: "/study/session/:studyId", element: <p>Session opened</p> },
    { path: "/study/training/:studyId", element: <p>Training opened</p> },
    { path: "/learn/lessons", element: <p>Lesson list</p> },
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
    await user.click(screen.getByRole("button", { name: "Start my block" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/study/session/st1"));
    expect(posts).toEqual([{ mode: "feynman" }]);
  });

  it("starts only once on a double click", async () => {
    const posts = recordPosts("/study-sessions", 202, started);
    const { user } = setup();
    const button = await screen.findByRole("button", { name: "Start my block" });
    await user.dblClick(button);
    await screen.findByText("Session opened");
    expect(posts).toHaveLength(1);
  });

  it("resumes the open session", async () => {
    const posts = recordPosts("/study-sessions", 202, started);
    const { router, user } = setup(summaryOut({ open_session_id: "st9" }));
    await user.click(await screen.findByRole("button", { name: "Resume my session" }));
    expect(router.state.location.pathname).toBe("/study/session/st9");
    expect(screen.queryByRole("button", { name: "Start my block" })).not.toBeInTheDocument();
    expect(posts).toHaveLength(0);
  });

  it("goes to the open session instead of showing study_already_open", async () => {
    recordPosts(
      "/study-sessions",
      409,
      apiError(
        "study_already_open",
        "Finish the open study session on the other lesson before starting this one.",
        { study_session_id: "st9" },
      ),
    );
    const { router, user } = setup();
    await user.click(await screen.findByRole("button", { name: "Start my block" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/study/session/st9"));
  });

  it("reopens the training that is blocking a guided session", async () => {
    recordPosts(
      "/study-sessions",
      409,
      apiError("study_already_open", "Finish the open training session before starting this one.", {
        study_session_id: "training-1",
        kind: "training",
      }),
    );
    const { router, user } = setup();
    await user.click(await screen.findByRole("button", { name: "Start my block" }));
    expect(await screen.findByText("Training opened")).toBeVisible();
    expect(router.state.location.pathname).toBe("/study/training/training-1");
  });

  it("offers to choose a lesson on no_block_today", async () => {
    recordPosts(
      "/study-sessions",
      404,
      apiError("no_block_today", "Nothing is scheduled today. Choose a lesson."),
    );
    const { router, user } = setup();
    await user.click(await screen.findByRole("button", { name: "Start my block" }));
    expect(
      await screen.findByRole("heading", { name: "No block planned today" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choose a lesson" }));
    expect(router.state.location.pathname).toBe("/learn/lessons");
  });

  it("shows an empty state with an action when there is no block and no session", async () => {
    const { user, router } = setup(summaryOut({ block: null }));
    expect(
      await screen.findByRole("heading", { name: "No block planned today" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choose a lesson" }));
    expect(router.state.location.pathname).toBe("/learn/lessons");
  });

  it("shows another start error inline and keeps the button", async () => {
    const message = "The lesson for this module isn't ready yet.";
    recordPosts("/study-sessions", 409, apiError("lesson_not_ready", message));
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Start my block" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(screen.getByRole("button", { name: "Start my block" })).toBeEnabled();
  });

  it("preselects the lesson from ?lesson", async () => {
    const posts = recordPosts("/study-sessions", 202, started);
    const { router, user } = setup(summaryOut(), "/study/session?lesson=l1");
    expect(await screen.findByRole("heading", { name: "Les API REST" })).toBeInTheDocument();
    expect(screen.queryByText("Your block for today")).not.toBeInTheDocument();
    expect(screen.queryByText("Your question for the tutor")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Study this lesson" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/study/session/st1"));
    expect(posts).toEqual([{ lesson_id: "l1", mode: "socratic" }]);
  });

  it("asks the tutor about a passage in direct mode, cut at 2000 characters", async () => {
    const posts = recordPosts("/study-sessions", 202, started);
    const passage = "x".repeat(2500);
    const { user } = setup(summaryOut(), {
      pathname: "/study/session",
      state: { lessonId: "l1", question: passage },
    } as InitialEntry);
    expect(await screen.findByText("Your question for the tutor")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Direct/ })).toBeChecked();
    await user.click(screen.getByRole("button", { name: "Ask the tutor my question" }));
    await waitFor(() => expect(posts).toHaveLength(1));
    expect(posts[0]).toEqual({ lesson_id: "l1", mode: "direct", question: "x".repeat(2000) });
  });

  it("keeps the open session within reach when a lesson is chosen", async () => {
    const { router, user } = setup(
      summaryOut({ open_session_id: "st9" }),
      "/study/session?lesson=l1",
    );
    await screen.findByRole("heading", { name: "Les API REST" });
    await user.click(screen.getByRole("button", { name: "Resume my session" }));
    expect(router.state.location.pathname).toBe("/study/session/st9");
  });

  it("announces the loading", () => {
    setup(() => new Promise<Response>(() => {}));
    expect(screen.getByRole("status")).toHaveTextContent("Loading your block for today…");
  });

  it("shows an error with a retry button", async () => {
    let calls = 0;
    const { user } = setup(() => {
      calls += 1;
      return calls === 1
        ? HttpResponse.json(apiError("boom", "The server is unavailable."), { status: 500 })
        : HttpResponse.json(summaryOut());
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("The server is unavailable.");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: "Start my block" })).toBeInTheDocument();
  });

  it("never opens a browser dialog", async () => {
    const dialog = vi.spyOn(window, "confirm");
    recordPosts("/study-sessions", 202, started);
    const { user } = setup();
    await user.click(await screen.findByRole("button", { name: "Start my block" }));
    expect(dialog).not.toHaveBeenCalled();
  });
});
