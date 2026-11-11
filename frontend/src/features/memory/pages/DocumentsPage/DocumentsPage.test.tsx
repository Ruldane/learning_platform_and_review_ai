import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { completed, failed, started } from "@/shared/realtime/testEvents";
import type { SessionEvent } from "@/shared/realtime/types";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { server } from "@/test/server";
import { API, apiError, documentOut, memoryBackend, readHandlers } from "../../fixtures";
import { renderRoutes } from "@/test/renderRoutes";
import { DocumentsPage } from "./DocumentsPage";

const SESSION = `${apiBaseUrl}/api/v1/sessions/s1`;

function setup(init: Parameters<typeof memoryBackend>[0] = {}) {
  const backend = memoryBackend(init);
  const fake = createFakeSocketServer();
  server.use(...readHandlers(backend));
  const view = renderRoutes(
    [{ path: "/memoire/documents", element: <DocumentsPage createSocket={fake.factory} /> }],
    "/memoire/documents",
  );
  return { backend, fake, ...view };
}

const written = (seq: number, title: string): SessionEvent => ({
  id: `e${seq}`,
  session_id: "s1",
  seq,
  ts: "2026-11-11T10:00:00Z",
  agent: "archivist",
  type: "memory.written",
  payload: { item_id: `a${seq}`, kind: "acquis", title, reason: "Extrait.", status: "active" },
});

const sessionView = (status: string) => ({
  id: "s1",
  graph: "learned_document",
  status,
  last_seq: 0,
  pending_interrupt: null,
  error: null,
  tokens_in: 0,
  tokens_out: 0,
  cost_usd: 0,
  created_at: "2026-11-11T10:00:00Z",
  updated_at: "2026-11-11T10:00:00Z",
});

describe("DocumentsPage import", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("an imported PDF goes from En file to Indexé without a reload", async () => {
    let contentType = "";
    const { backend, user } = setup();
    server.use(
      http.post(`${API}/documents`, ({ request }) => {
        contentType = request.headers.get("content-type") ?? "";
        const document = documentOut({ id: "d9", name: "cours.pdf", status: "queued" });
        backend.documents = [document];
        return HttpResponse.json({ document, duplicate: false }, { status: 202 });
      }),
      http.get(`${API}/documents`, () => {
        const snapshot = backend.documents;
        // Le worker finit entre deux lectures : la lecture suivante voit le document indexé.
        backend.documents = snapshot.map((d) => ({ ...d, status: "indexed" as const }));
        return HttpResponse.json(snapshot);
      }),
    );
    expect(await screen.findByText("Aucun document importé")).toBeInTheDocument();
    const pdf = new File(["%PDF-1.4"], "cours.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText("Choisir un fichier"), pdf);
    expect(await screen.findByText("En file")).toBeInTheDocument();
    expect(contentType).toMatch(/^multipart\/form-data; boundary=/);
    await vi.advanceTimersByTimeAsync(2000);
    expect(await screen.findByText("Indexé")).toBeInTheDocument();
  });

  it("empties the pasted-text form after a successful import, keeps it after a failure", async () => {
    const { backend, user } = setup();
    const bodies: unknown[] = [];
    let refuse = true;
    server.use(
      http.post(`${API}/documents/text`, async ({ request }) => {
        bodies.push(await request.json());
        if (refuse) return apiError("paste_too_long", "Texte trop long : 500 000 caractères.", 413);
        const document = documentOut({ id: "d2", name: "Notes", source_kind: "paste" });
        backend.documents = [document];
        return HttpResponse.json({ document, duplicate: false }, { status: 202 });
      }),
    );
    await user.click(await screen.findByRole("tab", { name: "Texte collé" }));
    await user.type(screen.getByLabelText("Texte"), "Mon cours");
    await user.click(screen.getByRole("button", { name: "Importer le texte" }));
    expect(await screen.findByText("Texte trop long : 500 000 caractères.")).toBeInTheDocument();
    expect(screen.getByLabelText("Texte")).toHaveValue("Mon cours");
    refuse = false;
    await user.click(screen.getByRole("button", { name: "Importer le texte" }));
    await waitFor(() => expect(screen.getByLabelText("Texte")).toHaveValue(""));
    expect(bodies).toEqual([
      { text: "Mon cours", title: null },
      { text: "Mon cours", title: null },
    ]);
    expect(await screen.findByText("Texte collé", { selector: "span" })).toBeInTheDocument();
  });

  it("says when a link was already imported", async () => {
    const { user } = setup();
    server.use(
      http.post(`${API}/documents`, () =>
        HttpResponse.json({ document: documentOut(), duplicate: true }, { status: 200 }),
      ),
    );
    await user.click(await screen.findByRole("tab", { name: "Lien" }));
    await user.type(screen.getByLabelText("Adresse du lien"), "https://exemple.fr/cours");
    await user.click(screen.getByRole("button", { name: "Importer le lien" }));
    expect(await screen.findByText("Ce contenu est déjà dans ta mémoire.")).toBeInTheDocument();
  });

  it("shows a retryable error when the list fails", async () => {
    const { user } = setup();
    let calls = 0;
    server.use(
      http.get(`${API}/documents`, () => {
        calls += 1;
        return calls === 1 ? apiError("boom", "Liste indisponible.", 500) : HttpResponse.json([]);
      }),
    );
    expect(await screen.findByText("Liste indisponible.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Réessayer" }));
    expect(await screen.findByText("Aucun document importé")).toBeInTheDocument();
  });
});

describe("DocumentsPage Déjà appris", () => {
  beforeEach(() => {
    useSessionStore.getState().reset("s1");
    server.use(http.get(SESSION, () => HttpResponse.json(sessionView("running"))));
  });
  afterEach(() => useSessionStore.getState().reset("s1"));

  async function start() {
    const view = setup({ documents: [documentOut({ id: "d1", name: "Cours NLP" })] });
    server.use(
      http.post(`${API}/documents/d1/learned`, () => {
        view.backend.documents = [documentOut({ id: "d1", name: "Cours NLP", learned: true })];
        return HttpResponse.json({ session_id: "s1" }, { status: 202 });
      }),
    );
    await view.user.click(await screen.findByRole("button", { name: "Déjà appris" }));
    await waitFor(() => expect(view.fake.sockets).toHaveLength(1));
    return view;
  }

  it("streams the Archiviste progress, then counts the acquis written", async () => {
    const { fake } = await start();
    expect(await screen.findByText("L'Archiviste extrait les concepts…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Déjà appris" })).toBeDisabled();
    fake
      .last()
      .open()
      .push(started(1, "archivist"), written(2, "Attention"), written(3, "Softmax"));
    fake.last().push(completed(4));
    expect(await screen.findByText("2 acquis ajouté(s)")).toBeInTheDocument();
    expect(await screen.findByText("Marqué déjà appris")).toBeInTheDocument();
  });

  it("does not count a proposed decision as an added acquis", async () => {
    const { fake } = await start();
    const pending = written(3, "Viser le NLP");
    if (pending.type === "memory.written") pending.payload.status = "pending";
    fake.last().open().push(written(2, "Attention"), pending, completed(4));
    expect(await screen.findByText("1 acquis ajouté(s)")).toBeInTheDocument();
  });

  it("shows the failure message of the run", async () => {
    const { fake } = await start();
    fake.last().open().push(started(1, "archivist"), failed(2));
    expect(await screen.findByRole("alert")).toHaveTextContent("Clé manquante pour ce niveau.");
  });

  it("shows the server refusal when the document cannot be marked", async () => {
    const { user } = setup({ documents: [documentOut({ id: "d1" })] });
    server.use(
      http.post(`${API}/documents/d1/learned`, () =>
        apiError("document_not_indexed", "Le document n'est pas encore indexé.", 409),
      ),
    );
    await user.click(await screen.findByRole("button", { name: "Déjà appris" }));
    expect(await screen.findByText("Le document n'est pas encore indexé.")).toBeInTheDocument();
  });
});
