import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { API, programApi, programOut } from "@/test/programApi";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { ProgramPage } from "./ProgramPage";

function setup(program: Record<string, unknown> = programOut()) {
  const { handlers, state } = programApi({ program });
  server.use(...handlers);
  const view = renderRoutes(
    [
      { path: "/apprendre/programme/:programId", element: <ProgramPage /> },
      { path: "/apprendre/lecons/:lessonId", element: <h1>Leçon ouverte</h1> },
    ],
    "/apprendre/programme/p1",
  );
  return { ...view, state };
}

const MOVE_T1 = "Déplacer « Lire le chapitre 1 »";

describe("ProgramPage", () => {
  it("shows the program, its week with the calendar and the load against 85 %", async () => {
    setup();
    expect(
      await screen.findByRole("heading", { name: "Python pour la data", level: 1 }),
    ).toBeInTheDocument();
    expect(screen.getByText("Brouillon")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Semaine 1 : Premiers pas en Python" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Calendrier de la semaine 1" })).toBeInTheDocument();
    expect(screen.getByText("3 h / 11 h 54 (85 %)")).toBeInTheDocument();
  });

  it("moves a task and reads the program again", async () => {
    let body: unknown = null;
    let reads = 0;
    const { user } = setup();
    server.use(
      http.patch(`${API}/tasks/t1`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({});
      }),
      http.get(`${API}/programs/p1`, () => {
        reads += 1;
        return HttpResponse.json(programOut());
      }),
    );
    await user.click(await screen.findByRole("button", { name: MOVE_T1 }));
    await user.click(screen.getByRole("menuitem", { name: /jeudi 19 novembre/ }));
    await screen.findByRole("group", { name: "Calendrier de la semaine 1" });
    expect(body).toEqual({ planned_date: "2026-11-19" });
    await waitFor(() => expect(reads).toBeGreaterThan(0));
  });

  it("shows a 422 over budget inline and puts the task back", async () => {
    const { user } = setup();
    server.use(
      http.patch(`${API}/tasks/t1`, () =>
        HttpResponse.json(
          {
            error: {
              code: "week_over_budget",
              message: "Semaine 2 : 760 min prévues, 714 au plus.",
              details: { week_rank: 2, planned_minutes: 760, cap_minutes: 714 },
            },
          },
          { status: 422 },
        ),
      ),
    );
    await user.click(await screen.findByRole("button", { name: MOVE_T1 }));
    await user.click(screen.getByRole("menuitem", { name: /jeudi 19 novembre/ }));
    expect(
      await screen.findByText("Semaine 2 : 760 min prévues, 714 au plus."),
    ).toBeInTheDocument();
    const monday = screen.getByRole("group", { name: "lun. 16 nov." });
    expect(await within(monday).findByText("Lire le chapitre 1")).toBeInTheDocument();
  });

  it("chooses the week to show", async () => {
    const { user } = setup();
    await user.selectOptions(
      await screen.findByRole("combobox", { name: "Semaine affichée" }),
      "2",
    );
    expect(
      screen.getByRole("heading", { name: "Semaine 2 : Données et fichiers" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Lire le module csv")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Semaine précédente" }));
    expect(
      screen.getByRole("heading", { name: "Semaine 1 : Premiers pas en Python" }),
    ).toBeInTheDocument();
  });

  it("offers the PDF and .ics exports as links", async () => {
    setup();
    const pdf = await screen.findByRole("link", { name: "Exporter en PDF" });
    expect(pdf).toHaveAttribute("href", expect.stringMatching(/\/programs\/p1\/export\.pdf$/));
    expect(screen.getByRole("link", { name: "Exporter le calendrier (.ics)" })).toHaveAttribute(
      "href",
      expect.stringMatching(/\/programs\/p1\/export\.ics$/),
    );
  });

  it("lists every task and the lesson of each module in the list view", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("tab", { name: "Liste" }));
    expect(screen.getByText("Pratiquer le tri")).toBeInTheDocument();
    const lessons = screen.getByRole("region", { name: "Leçons du programme" });
    expect(within(lessons).getByText("Prête")).toBeInTheDocument();
    expect(within(lessons).getByText("En préparation")).toBeInTheDocument();
    await user.click(
      within(lessons).getByRole("link", { name: /Ouvrir la leçons*: Bases du langage/ }),
    );
    expect(await screen.findByRole("heading", { name: "Leçon ouverte" })).toBeInTheDocument();
  });

  it("toggles a task as done from the list view", async () => {
    let body: unknown = null;
    const { user } = setup();
    server.use(
      http.patch(`${API}/tasks/t1`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({});
      }),
    );
    await user.click(await screen.findByRole("tab", { name: "Liste" }));
    await user.click(
      screen.getByRole("checkbox", { name: "Marquer « Lire le chapitre 1 » comme faite" }),
    );
    await waitFor(() => expect(body).toEqual({ status: "done" }));
  });

  it("shows the overall progress", async () => {
    const { user } = setup();
    await user.click(await screen.findByRole("tab", { name: "Avancement" }));
    expect(screen.getByRole("region", { name: "Avancement du programme" })).toBeInTheDocument();
    expect(screen.getByText("1 / 5")).toBeInTheDocument();
  });

  it("shows what a revision changed", async () => {
    setup(
      programOut({
        version: 2,
        diff: {
          added: ["Fichiers CSV / Lire le module csv"],
          removed: [],
          moved: [
            {
              task: "Bases du langage / Lire le chapitre 1",
              before: "2026-11-16",
              after: "2026-11-18",
            },
          ],
          weeks_before: 2,
          weeks_after: 2,
        },
      }),
    );
    const changes = await screen.findByRole("region", {
      name: "Changements de la dernière version",
    });
    expect(within(changes).getByText("Lire le module csv")).toBeInTheDocument();
    expect(within(changes).getByText("lun. 16 nov. → mer. 18 nov.")).toBeInTheDocument();
  });

  it("offers « Réessayer » when the program cannot be read", async () => {
    let calls = 0;
    server.use(
      http.get(`${API}/programs/p1`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({}, { status: 500 })
          : HttpResponse.json(programOut());
      }),
      http.get(`${API}/sessions/s1`, () => HttpResponse.json({}, { status: 404 })),
    );
    const { user } = renderRoutes(
      [{ path: "/apprendre/programme/:programId", element: <ProgramPage /> }],
      "/apprendre/programme/p1",
    );
    await user.click(await screen.findByRole("button", { name: "Réessayer" }));
    expect(await screen.findByRole("heading", { name: "Python pour la data" })).toBeInTheDocument();
  });
});
