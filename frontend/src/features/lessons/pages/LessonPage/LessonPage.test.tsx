import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, lessonOut, resourceOut } from "@/test/lessonsApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { LessonPage } from "./LessonPage";

function setup(lesson: Record<string, unknown> = lessonOut()) {
  server.use(http.get(`${API}/lessons/l1`, () => HttpResponse.json(lesson)));
  return renderRoutes(
    [
      { path: "/apprendre/lecons/:lessonId", element: <LessonPage /> },
      { path: "/apprendre/lecons", element: <h1>Toutes les leçons</h1> },
    ],
    "/apprendre/lecons/l1",
  );
}

describe("LessonPage", () => {
  it("renders the lesson, its resources and the PDF link", async () => {
    setup();
    expect(
      await screen.findByRole("heading", { name: "Les variables et les types", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText("Une variable nomme une valeur.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Télécharger le PDF" })).toHaveAttribute(
      "href",
      expect.stringMatching(/\/lessons\/l1\/pdf$/),
    );
    const list = screen.getByRole("list", { name: "Ressources" });
    expect(
      within(list).getByRole("link", { name: /Documentation officielle de Python/ }),
    ).toBeInTheDocument();
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
        name: "Marquer « Documentation officielle de Python » comme lue",
      }),
    );
    await waitFor(() => expect(body).toEqual({ status: "read" }));
  });

  it("says a lesson is being prepared, not the empty reader", async () => {
    setup(lessonOut({ status: "generating", markdown: "", word_count: 0, pdf_available: false }));
    expect(await screen.findByText("Leçon en préparation")).toBeInTheDocument();
    expect(screen.getByText(/Le Rédacteur écrit la leçon/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Télécharger le PDF" })).toBeNull();
    expect(screen.queryByRole("list", { name: "Ressources" })).toBeNull();
  });

  it("says when a pending lesson will start", async () => {
    setup(lessonOut({ status: "pending", week_rank: 3, markdown: "", word_count: 0 }));
    expect(await screen.findByText("Leçon en préparation")).toBeInTheDocument();
    expect(
      screen.getByText("Cette leçon sera préparée 7 jours avant le début de la semaine 3."),
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
    expect(await screen.findByText("La préparation de la leçon a échoué")).toBeInTheDocument();
    expect(
      screen.getByText(
        "La production de la leçon s'est arrêtée avant la fin : elle sera relancée.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Une nouvelle tentative aura lieu automatiquement (3 essais au plus)."),
    ).toBeInTheDocument();
  });

  it("goes back to the lessons", async () => {
    const { router, user } = setup();
    await user.click(await screen.findByRole("link", { name: "Toutes les leçons" }));
    expect(router.state.location.pathname).toBe("/apprendre/lecons");
  });

  it("offers « Réessayer » when the lesson cannot be read", async () => {
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
      [{ path: "/apprendre/lecons/:lessonId", element: <LessonPage /> }],
      "/apprendre/lecons/l1",
    );
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    expect(
      await screen.findByRole("heading", { name: "Les variables et les types" }),
    ).toBeInTheDocument();
  });
});
