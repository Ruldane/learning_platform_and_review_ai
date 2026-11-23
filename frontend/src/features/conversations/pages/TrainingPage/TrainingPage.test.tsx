import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { TrainingPage } from "./TrainingPage";

const API = "http://localhost:8000/api/v1/study-sessions/training";
const STUDY_ID = "10ccb9f9-40e1-4243-8dd5-78189a93278f";
const LIST = "http://localhost:8000/api/v1/conversations/training";
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
  beforeEach(() => server.use(http.get(LIST, () => HttpResponse.json([]))));
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
  it("starts an independent conversation from the sidebar while an older one stays open", async () => {
    const nextId = "20ccb9f9-40e1-4243-8dd5-78189a93278f";
    const previous = { id: STUDY_ID, title: "Chaînes et modèles", updated_at: training.started_at };
    let created = false;
    server.use(
      http.get(LIST, () =>
        HttpResponse.json(
          created
            ? [{ ...previous, id: nextId, title: "Nouvelle conversation" }, previous]
            : [previous],
        ),
      ),
      http.get(`${API}/open`, () => HttpResponse.json(training)),
      http.get(`${API}/:id`, ({ params }) =>
        HttpResponse.json({
          ...training,
          id: params.id,
          mode: params.id === STUDY_ID ? "direct" : "socratic",
        }),
      ),
      http.post(API, async ({ request }) => {
        expect(await request.json()).toMatchObject({ new_conversation: true, mode: "socratic" });
        created = true;
        return HttpResponse.json({ ...training, id: nextId }, { status: 202 });
      }),
    );
    const { user, router } = setup();
    expect(await screen.findByText(greeting)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Nouvelle conversation" }));
    await user.click(await screen.findByRole("button", { name: "Commencer le training" }));
    await waitFor(() => expect(router.state.location.pathname).toContain(nextId));
    await user.click(await screen.findByRole("button", { name: "Ouvrir Chaînes et modèles" }));
    await waitFor(() =>
      expect(screen.getByRole("combobox", { name: "Mode d’apprentissage" })).toHaveValue("direct"),
    );
    expect(router.state.location.pathname).toContain(STUDY_ID);
  });
});
