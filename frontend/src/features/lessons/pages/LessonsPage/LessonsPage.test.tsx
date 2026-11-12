import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, lessonSummary } from "@/test/lessonsApi";
import { summaryOut } from "@/test/programApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { LessonsPage } from "./LessonsPage";

const routes = [
  { path: "/apprendre/lecons", element: <LessonsPage /> },
  { path: "/apprendre/lecons/:lessonId", element: <h1>Leçon ouverte</h1> },
  { path: "/apprendre/programme/:programId", element: <h1>Programme ouvert</h1> },
  { path: "/apprendre/conseil", element: <h1>Conseil ouvert</h1> },
];

function setup(lessons: Record<string, unknown>[], programs: unknown[] = [summaryOut()]) {
  server.use(
    http.get(`${API}/programs`, () => HttpResponse.json(programs)),
    http.get(`${API}/programs/p1/lessons`, () => HttpResponse.json(lessons)),
  );
  return renderRoutes(routes, "/apprendre/lecons");
}

describe("LessonsPage", () => {
  it("lists the lessons of the latest program by week, with their state", async () => {
    const { router, user } = setup([
      lessonSummary(),
      lessonSummary({ id: "l2", title: "Les fichiers CSV", week_rank: 2, status: "generating" }),
      lessonSummary({ id: "l3", title: "Les dates", week_rank: 3, status: "pending" }),
      lessonSummary({ id: "l4", title: "Les API", week_rank: 3, status: "failed" }),
    ]);
    const week2 = await screen.findByRole("region", { name: "Semaine 2" });
    expect(within(week2).getByText("En préparation")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Semaine 3" })).getByText("À venir"),
    ).toBeInTheDocument();
    expect(screen.getByText("Nouvelle tentative prévue")).toBeInTheDocument();
    expect(screen.getByText("1 400 mots")).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Lire « Les variables et les types »" }));
    expect(router.state.location.pathname).toBe("/apprendre/lecons/l1");
  });

  it("explains that lessons come with the validated program", async () => {
    const { router, user } = setup([]);
    expect(await screen.findByText("Pas encore de leçon")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voir le programme" }));
    expect(router.state.location.pathname).toBe("/apprendre/programme/p1");
  });

  it("sends to the council when there is no program", async () => {
    const { router, user } = setup([], []);
    expect(await screen.findByText("Pas encore de programme")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Ouvrir le Conseil" }));
    expect(router.state.location.pathname).toBe("/apprendre/conseil");
  });

  it("offers « Réessayer » when the lessons cannot be read", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/programs`, () => HttpResponse.json([summaryOut()])),
      http.get(`${API}/programs/p1/lessons`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({}, { status: 500 })
          : HttpResponse.json([lessonSummary()]);
      }),
    );
    const { user } = renderRoutes(routes, "/apprendre/lecons");
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Les variables et les types")).toBeInTheDocument();
  });
});
