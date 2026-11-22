import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import type { components } from "@/shared/api/schema";
import { API } from "@/test/councilApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { ProjectionPage } from "./ProjectionPage";

const data: components["schemas"]["FutureSelfOut"] = {
  as_of: "2026-11-16",
  role: "Ingénieur IA",
  zone: "France",
  program_id: "p1",
  sample: { run_id: "r1", finished_at: "2026-11-15T12:00:00Z", analyzed: 4 },
  offer_count: 4,
  current_percent: 25,
  target_percent: 60,
  observed_weeks: 4,
  scenarios: [
    { kind: "observed", weekly_minutes: 120, target_date: "2026-11-23", projected_percent: 75 },
    { kind: "planned", weekly_minutes: 180, target_date: "2026-11-21", projected_percent: 75 },
  ],
  recommendations: [
    {
      chapter: {
        program_id: "p1",
        module_id: "m1",
        lesson_id: "l1",
        title: "Recherche augmentée",
        minutes: 120,
        skills: ["RAG"],
      },
      offers_unlocked: 2,
      offers_improved: 2,
      score_points: 200,
    },
  ],
  uncertainty: ["small_offer_sample"],
};

function renderProjection() {
  return renderRoutes(
    [
      { path: "/carriere/futur", Component: ProjectionPage },
      { path: "/apprendre/lecons/l1", element: <h1>Leçon de recette</h1> },
    ],
    "/carriere/futur",
  );
}

it("simule une autre disponibilité et ouvre le chapitre au clavier", async () => {
  const requests: URLSearchParams[] = [];
  server.use(
    http.get(API + "/future-self", ({ request }) => {
      const query = new URL(request.url).searchParams;
      requests.push(query);
      return HttpResponse.json({
        ...data,
        scenarios: query.has("alternative_weekly_minutes")
          ? [
              ...data.scenarios,
              {
                kind: "alternative",
                weekly_minutes: 240,
                target_date: "2026-11-20",
                projected_percent: 75,
              },
            ]
          : data.scenarios,
      });
    }),
  );
  const { user, router } = renderProjection();
  expect(await screen.findByRole("heading", { name: "Rythme observé" })).toBeVisible();
  const role = screen.getByRole("textbox", { name: "Poste visé" });
  const hours = screen.getByRole("spinbutton", { name: "Heures par semaine à simuler" });
  await user.tab();
  expect(role).toHaveFocus();
  await user.tab();
  expect(screen.getByRole("textbox", { name: "Zone du radar" })).toHaveFocus();
  await user.tab();
  expect(hours).toHaveFocus();
  await user.keyboard("4{Enter}");

  const alternative = await screen.findByRole("region", { name: "Disponibilité simulée" });
  expect(within(alternative).getByText("vendredi 20 novembre")).toBeVisible();
  expect(requests.at(-1)?.get("alternative_weekly_minutes")).toBe("240");
  expect(screen.getByRole("link", { name: "Proposer une replanification" })).toHaveAttribute(
    "href",
    "/apprendre/programme/p1/replanification",
  );

  const chapter = screen.getByRole("link", { name: "Recherche augmentée" });
  for (let step = 0; step < 6 && document.activeElement !== chapter; step += 1) {
    await user.tab();
  }
  expect(chapter).toHaveFocus();
  await user.keyboard("{Enter}");
  expect(router.state.location.pathname).toBe("/apprendre/lecons/l1");
  expect(await screen.findByRole("heading", { name: "Leçon de recette" })).toBeVisible();
});

it("explique les données manquantes sans présenter de date", async () => {
  server.use(
    http.get(API + "/future-self", () =>
      HttpResponse.json({
        ...data,
        role: null,
        program_id: null,
        sample: null,
        offer_count: 0,
        current_percent: null,
        observed_weeks: 0,
        scenarios: [
          { kind: "observed", weekly_minutes: null, target_date: null, projected_percent: null },
        ],
        recommendations: [],
        uncertainty: ["insufficient_study_history", "no_offer_sample"],
      }),
    ),
  );
  renderProjection();
  expect(
    await screen.findByText("Aucune offre exploitable pour ce poste et cette zone."),
  ).toBeVisible();
  expect(
    screen.getByText("Il faut deux semaines complètes pour estimer ton rythme."),
  ).toBeVisible();
  expect(screen.queryByRole("link", { name: "Proposer une replanification" })).toBeNull();
});
