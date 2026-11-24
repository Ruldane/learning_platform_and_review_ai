import { act, screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";
import { API, lessonOut, resourceOut } from "@/test/lessonsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { LessonPage } from "./LessonPage";

function setup(lesson: Record<string, unknown> = lessonOut()) {
  server.use(http.get(`${API}/lessons/l1`, () => HttpResponse.json(lesson)));
  return renderRoutes(
    [
      { path: "/learn/lessons/:lessonId", element: <LessonPage /> },
      { path: "/learn/lessons", element: <h1>Toutes les leçons</h1> },
    ],
    "/learn/lessons/l1",
  );
}

describe("LessonPage", () => {
  it("renders the lesson, its resources and the PDF link", async () => {
    setup();
    expect(
      await screen.findByRole("heading", { name: "Les variables et les types", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText("Une variable nomme une valeur.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download PDF" })).toHaveAttribute(
      "href",
      expect.stringMatching(/\/lessons\/l1\/pdf$/),
    );
    const list = screen.getByRole("list", { name: "Resources" });
    expect(
      within(list).getByRole("link", { name: /Documentation officielle de Python/ }),
    ).toBeInTheDocument();
  });

  it("reads a ready lesson again until its PDF is there", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      let reads = 0;
      server.use(
        http.get(`${API}/lessons/l1`, () => {
          reads += 1;
          return HttpResponse.json(lessonOut({ pdf_available: reads > 1 }));
        }),
      );
      renderRoutes(
        [{ path: "/learn/lessons/:lessonId", element: <LessonPage /> }],
        "/learn/lessons/l1",
      );
      expect(await screen.findByText("Une variable nomme une valeur.")).toBeInTheDocument();
      expect(screen.queryByRole("link", { name: "Download PDF" })).toBeNull();
      await act(() => vi.advanceTimersByTimeAsync(5000));
      expect(await screen.findByRole("link", { name: "Download PDF" })).toBeInTheDocument();
      await act(() => vi.advanceTimersByTimeAsync(60_000));
      expect(reads).toBe(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps the published chapter and its PDF visible during verification", async () => {
    setup(lessonOut({ verification_session_id: "verification-1" }));

    expect(await screen.findByRole("status", { name: "To verify" })).toBeInTheDocument();
    expect(screen.getByText("Une variable nomme une valeur.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download PDF" })).toBeInTheDocument();
  });

  it("shows the verification of a new draft instead of the reader", async () => {
    setup(
      lessonOut({
        status: "generating",
        markdown: "",
        pdf_available: false,
        verification_session_id: "verification-1",
      }),
    );

    expect(await screen.findByRole("status", { name: "To verify" })).toBeInTheDocument();
    expect(screen.queryByText(/The Writer is writing the lesson/)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Download PDF" })).not.toBeInTheDocument();
  });

  it("shows why a revision failed next to the previously published text", async () => {
    setup(lessonOut({ verification_failure_reason: "Le schéma du brouillon est incomplet." }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Le schéma du brouillon est incomplet.");
    expect(screen.getByText("Une variable nomme une valeur.")).toBeInTheDocument();
  });

  it("toggles a resource as read from the lesson", async () => {
    let body: unknown = null;
    const { user } = setup();
    server.use(
      http.patch(`${API}/resources/r1`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(resourceOut({ status: "read" }));
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: "Mark “Documentation officielle de Python” as read",
      }),
    );
    await waitFor(() => expect(body).toEqual({ status: "read" }));
  });

  it("says a lesson is being prepared, not the empty reader", async () => {
    setup(lessonOut({ status: "generating", markdown: "", word_count: 0, pdf_available: false }));
    expect(await screen.findByText("Lesson being prepared")).toBeInTheDocument();
    expect(screen.getByText(/The Writer is writing the lesson/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Download PDF" })).toBeNull();
    expect(screen.queryByRole("list", { name: "Resources" })).toBeNull();
  });

  it("says when a pending lesson will start", async () => {
    setup(lessonOut({ status: "pending", week_rank: 3, markdown: "", word_count: 0 }));
    expect(await screen.findByText("Lesson being prepared")).toBeInTheDocument();
    expect(
      screen.getByText("This lesson will be prepared 7 days before week 3 starts."),
    ).toBeInTheDocument();
  });

  it("shows the reason of a failure and the automatic next attempt", async () => {
    setup(
      lessonOut({
        status: "failed",
        failure_reason:
          "La production de la leçon s'est arrêtée avant la fin : elle sera relancée.",
        markdown: "",
      }),
    );
    expect(await screen.findByText("Lesson preparation failed")).toBeInTheDocument();
    expect(
      screen.getByText(
        "La production de la leçon s'est arrêtée avant la fin : elle sera relancée.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("A new attempt will happen automatically (3 tries max)."),
    ).toBeInTheDocument();
  });

  it("goes back to the lessons", async () => {
    const { router, user } = setup();
    await user.click(await screen.findByRole("link", { name: "All lessons" }));
    expect(router.state.location.pathname).toBe("/learn/lessons");
  });

  it("offers Retry when the lesson cannot be read", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/lessons/l1`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({}, { status: 500 })
          : HttpResponse.json(lessonOut());
      }),
    );
    const { user } = renderRoutes(
      [{ path: "/learn/lessons/:lessonId", element: <LessonPage /> }],
      "/learn/lessons/l1",
    );
    await user.click(await screen.findByRole("button", { name: "Retry" }));
    expect(
      await screen.findByRole("heading", { name: "Les variables et les types" }),
    ).toBeInTheDocument();
  });
});
