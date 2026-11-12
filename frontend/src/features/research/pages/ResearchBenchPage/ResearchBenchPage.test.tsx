import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { renderRoutes } from "@/test/renderRoutes";
import { researchEvents } from "@/test/researchEvents";
import { server } from "@/test/server";
import { ResearchBenchPage } from "./ResearchBenchPage";

const API = `${apiBaseUrl}/api/v1/sessions`;
const sessionView = (status: string, lastSeq = 0) => ({
  id: "s1",
  graph: "web_research",
  status,
  subject_type: null,
  subject_id: null,
  last_seq: lastSeq,
  pending_interrupt: null,
  error: null,
  tokens_in: 0,
  tokens_out: 0,
  cost_usd: 0,
  created_at: "2026-11-12T10:00:00Z",
  updated_at: "2026-11-12T10:00:00Z",
});
const apiError = (code: string, message: string) => ({ error: { code, message, details: null } });

function setup(route = "/reglages/recherche/essai") {
  const fake = createFakeSocketServer();
  const view = renderRoutes(
    [
      {
        path: "/reglages/recherche/essai",
        element: <ResearchBenchPage createSocket={fake.factory} />,
      },
      { path: "/reglages/recherche", element: <p>Réglages de recherche</p> },
    ],
    route,
  );
  return { fake, ...view };
}

describe("ResearchBenchPage", () => {
  beforeEach(() => {
    useSessionStore.getState().reset("s1");
    server.use(http.get(`${API}/s1`, () => HttpResponse.json(sessionView("running"))));
  });
  afterEach(() => useSessionStore.getState().reset("s1"));

  it("streams scored sources and flags an unreadable page", async () => {
    const posted: unknown[] = [];
    server.use(
      http.post(API, async ({ request }) => {
        posted.push(await request.json());
        return HttpResponse.json({ session_id: "s1" }, { status: 201 });
      }),
    );
    const { fake, router, user } = setup();
    await user.type(screen.getByLabelText("Requête"), "retrieval augmented generation");
    await user.type(screen.getByLabelText("Adresses supplémentaires"), "https://exemple.fr/doc");
    await user.click(screen.getByRole("button", { name: "Lancer l'essai" }));

    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    expect(posted).toEqual([
      {
        graph: "web_research",
        input: { query: "retrieval augmented generation", urls: ["https://exemple.fr/doc"] },
      },
    ]);
    expect(router.state.location.search).toBe("?session=s1");

    const { toolCalled, toolResult, sourceFound, completed } = researchEvents();
    fake
      .last()
      .open()
      .push(
        toolCalled("c1", "web_search", { query: "rag", lang: "en" }),
        toolResult("c1", true, "8 résultat(s) via searxng"),
        sourceFound({ source_id: "a", title: "Guide RAG", score: 82, verdict: "kept" }),
        sourceFound({
          source_id: "b",
          score: 41,
          verdict: "rejected",
          reason: "Trop superficielle.",
        }),
        sourceFound({
          source_id: "c",
          status: "unreadable",
          reason: "Page illisible : aucun texte principal trouvé.",
        }),
        completed(),
      );

    expect(await screen.findByText("82/100")).toBeInTheDocument();
    expect(screen.getByText("8 résultat(s) via searxng")).toBeInTheDocument();
    expect(screen.getByText("Trop superficielle.")).toBeInTheDocument();
    expect(
      within(screen.getByRole("region", { name: "Illisibles" })).getByText(
        "Page illisible : aucun texte principal trouvé.",
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText("Terminée")).toBeInTheDocument();
    expect(screen.queryByText("L'Éclaireur cherche…")).not.toBeInTheDocument();
  });

  it("keeps a replayed source once and shows an excluded domain without crashing", async () => {
    const { fake } = setup("/reglages/recherche/essai?session=s1");
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    const { sourceFound } = researchEvents();
    fake
      .last()
      .open()
      .push(
        sourceFound({ source_id: "a", title: "Guide RAG", score: 82, verdict: "kept" }),
        sourceFound({ source_id: "a", title: "Guide RAG", score: 82, verdict: "kept" }),
        sourceFound({
          url: "https://pinterest.com/x",
          title: "Épingle",
          status: "unreadable",
          reason: "Domaine exclu dans les réglages.",
        }),
      );
    expect(await screen.findByText("Domaine exclu dans les réglages.")).toBeInTheDocument();
    expect(screen.getAllByText("Guide RAG")).toHaveLength(1);
  });

  it("resumes the session given in ?session= after a reload", async () => {
    const { fake } = setup("/reglages/recherche/essai?session=s1");
    expect(screen.queryByRole("button", { name: "Lancer l'essai" })).not.toBeInTheDocument();
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    expect(fake.last().url).toContain("/s1");
    const { sourceFound } = researchEvents();
    fake
      .last()
      .open()
      .push(sourceFound({ source_id: "a", title: "Guide RAG", score: 70, verdict: "kept" }));
    expect(await screen.findByText("Guide RAG")).toBeInTheDocument();
  });

  it("shows the failure message of a failed run and offers a new attempt", async () => {
    const { fake, router, user } = setup("/reglages/recherche/essai?session=s1");
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    const { failed } = researchEvents();
    fake.last().open().push(failed("Aucun moteur de recherche n'a répondu."));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Aucun moteur de recherche n'a répondu.",
    );
    expect(screen.getByText("Échouée")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Nouvel essai" }));
    expect(await screen.findByRole("button", { name: "Lancer l'essai" })).toBeInTheDocument();
    expect(router.state.location.search).toBe("");
  });

  it("keeps the form and shows the error when the run cannot start", async () => {
    server.use(
      http.post(API, () =>
        HttpResponse.json(apiError("search_unavailable", "Recherche indisponible."), {
          status: 503,
        }),
      ),
    );
    const { user } = setup();
    await user.type(screen.getByLabelText("Requête"), "rag");
    await user.click(screen.getByRole("button", { name: "Lancer l'essai" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Recherche indisponible.");
    expect(screen.getByLabelText("Requête")).toHaveValue("rag");
  });

  it("offers another attempt when the session is unknown", async () => {
    const { fake, user } = setup("/reglages/recherche/essai?session=s1");
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    fake.last().drop(4404);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Nouvel essai" }));
    expect(await screen.findByRole("button", { name: "Lancer l'essai" })).toBeInTheDocument();
  });

  it("links back to the search settings", async () => {
    const { user } = setup();
    await user.click(screen.getByRole("link", { name: "Régler la recherche" }));
    expect(await screen.findByText("Réglages de recherche")).toBeInTheDocument();
  });
});
