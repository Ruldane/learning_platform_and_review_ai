import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { TrainingPage } from "./TrainingPage";

const API = "http://localhost:8000/api/v1/study-sessions/training";
const STUDY_ID = "10ccb9f9-40e1-4243-8dd5-78189a93278f";
const greeting = "Que veux-tu travailler aujourd’hui ?";
const training = {
  id: STUDY_ID,
  greeting,
  started_at: "2026-11-22T08:00:00Z",
  ended_at: null,
  minutes: 0,
  flashcards_created: 0,
  skills: [],
  summary: null,
  mode: "socratic",
  status: "open",
  conversation: {
    id: STUDY_ID,
    turns: [],
    usage: {
      thread_tokens: 0,
      thread_token_limit: 100000,
      day_tokens: 0,
      day_token_limit: 300000,
      turns: 0,
      turn_limit: 100,
    },
  },
};

function setup() {
  return renderRoutes(
    [{ path: "/etudier/training/:studyId?", element: <TrainingPage /> }],
    "/etudier/training",
  );
}

describe("TrainingPage", () => {
  it("starts without a lesson, keeps the same training while changing modes and shows the result", async () => {
    let mode = "socratic";
    const changes: unknown[] = [];
    server.use(http.get(`${API}/open`, () => HttpResponse.json(null)));
    server.use(http.post(API, () => HttpResponse.json(training, { status: 202 })));
    server.use(http.get(`${API}/${STUDY_ID}`, () => HttpResponse.json({ ...training, mode })));
    server.use(
      http.patch(`${API}/${STUDY_ID}`, async ({ request }) => {
        const payload = (await request.json()) as { action: string; mode: string };
        changes.push(payload);
        if (payload.action === "mode") {
          mode = payload.mode;
          return HttpResponse.json({ ...training, mode });
        }
        return HttpResponse.json({
          ...training,
          mode,
          status: "finished",
          minutes: 12,
          flashcards_created: 2,
          summary: "Tu as travaillé les chaînes.",
        });
      }),
    );

    const { user, router } = setup();
    await user.click(await screen.findByRole("button", { name: "Commencer le training" }));
    expect(await screen.findByText(greeting)).toBeVisible();
    const modeField = screen.getByRole("combobox", { name: "Mode d’apprentissage" });
    await user.selectOptions(modeField, "feynman");
    await waitFor(() => expect(modeField).toHaveValue("feynman"));
    expect(changes).toHaveLength(1);
    expect(router.state.location.pathname).toBe(`/etudier/training/${STUDY_ID}`);
    expect(screen.getByText(greeting)).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Terminer le training" }));
    expect(await screen.findByText("Tu as travaillé les chaînes.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Bilan du training" })).toHaveFocus();
    expect(screen.getByText(/12 min/)).toBeVisible();
    expect(screen.getByText(/2 fiches/)).toBeVisible();
  });

  it("reopens the existing training", async () => {
    server.use(http.get(`${API}/open`, () => HttpResponse.json({ ...training, mode: "direct" })));
    server.use(
      http.get(`${API}/${STUDY_ID}`, () => HttpResponse.json({ ...training, mode: "direct" })),
    );
    setup();
    expect(await screen.findByText(greeting)).toBeVisible();
    expect(screen.getByRole("combobox", { name: "Mode d’apprentissage" })).toHaveValue("direct");
    expect(screen.queryByRole("button", { name: "Commencer le training" })).toBeNull();
  });
});
