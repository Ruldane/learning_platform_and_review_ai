import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiBaseUrl } from "@/shared/api/client";
import { useSessionStore } from "@/shared/realtime/sessionStore";
import { completed, failed, started } from "@/shared/realtime/testEvents";
import type { SessionEvent } from "@/shared/realtime/types";
import { createFakeSocketServer } from "@/test/fakeSocket";
import { server } from "@/test/server";
import {
  API,
  apiError,
  documentOut,
  memoryBackend,
  readHandlers,
  sessionOut,
} from "../../fixtures";
import { renderRoutes } from "@/test/renderRoutes";
import { DocumentsPage } from "./DocumentsPage";

const SESSION = `${apiBaseUrl}/api/v1/sessions/s1`;

function setup(init: Parameters<typeof memoryBackend>[0] = {}) {
  const backend = memoryBackend(init);
  const fake = createFakeSocketServer();
  server.use(...readHandlers(backend));
  const view = renderRoutes(
    [{ path: "/memory/documents", element: <DocumentsPage createSocket={fake.factory} /> }],
    "/memory/documents",
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
  payload: { item_id: `a${seq}`, kind: "skill", title, reason: "Extrait.", status: "active" },
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
    expect(await screen.findByText("No imported documents")).toBeInTheDocument();
    const pdf = new File(["%PDF-1.4"], "cours.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText("Choose a file"), pdf);
    expect(await screen.findByText("Queued")).toBeInTheDocument();
    expect(contentType).toMatch(/^multipart\/form-data; boundary=/);
    await vi.advanceTimersByTimeAsync(2000);
    expect(await screen.findByText("Indexed")).toBeInTheDocument();
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
    await user.click(await screen.findByRole("tab", { name: "Pasted text" }));
    await user.type(screen.getByLabelText("Text"), "Mon cours");
    await user.click(screen.getByRole("button", { name: "Import text" }));
    expect(await screen.findByText("Texte trop long : 500 000 caractères.")).toBeInTheDocument();
    expect(screen.getByLabelText("Text")).toHaveValue("Mon cours");
    refuse = false;
    await user.click(screen.getByRole("button", { name: "Import text" }));
    await waitFor(() => expect(screen.getByLabelText("Text")).toHaveValue(""));
    expect(bodies).toEqual([
      { text: "Mon cours", title: null },
      { text: "Mon cours", title: null },
    ]);
    expect(await screen.findByText("Pasted text", { selector: "span" })).toBeInTheDocument();
  });

  it("says when a link was already imported", async () => {
    const { user } = setup();
    server.use(
      http.post(`${API}/documents`, () =>
        HttpResponse.json({ document: documentOut(), duplicate: true }, { status: 200 }),
      ),
    );
    await user.click(await screen.findByRole("tab", { name: "Link" }));
    await user.type(screen.getByLabelText("Link URL"), "https://exemple.fr/cours");
    await user.click(screen.getByRole("button", { name: "Import link" }));
    expect(await screen.findByText("This content is already in your memory.")).toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("No imported documents")).toBeInTheDocument();
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
    await view.user.click(await screen.findByRole("button", { name: "Already learned" }));
    await waitFor(() => expect(view.fake.sockets).toHaveLength(1));
    return view;
  }

  it("streams the Archiviste progress, then counts the acquis written", async () => {
    const { fake } = await start();
    const progress = await screen.findByText("The Archivist is extracting the concepts…");
    expect(progress).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Already learned" })).toBeDisabled();
    fake
      .last()
      .open()
      .push(started(1, "archivist"), written(2, "Attention"), written(3, "Softmax"));
    fake.last().push(completed(4));
    expect(await screen.findByText("2 acquired skill(s) added")).toBeInTheDocument();
    expect(await screen.findByText("Marked as already learned")).toBeInTheDocument();
  });

  it("does not count a proposed decision as an added acquis", async () => {
    const { fake } = await start();
    const pending = written(3, "Viser le NLP");
    if (pending.type === "memory.written") pending.payload.status = "pending";
    fake.last().open().push(written(2, "Attention"), pending, completed(4));
    expect(await screen.findByText("1 acquired skill(s) added")).toBeInTheDocument();
  });

  it("shows the failure message of the run", async () => {
    const { fake } = await start();
    fake.last().open().push(started(1, "archivist"), failed(2));
    expect(await screen.findByRole("alert")).toHaveTextContent("Clé manquante pour ce niveau.");
  });

  it("offers Relancer after a failure and follows the new run (I2)", async () => {
    const { fake, user } = await start();
    fake.last().open().push(started(1, "archivist"), failed(2));
    expect(await screen.findByRole("alert")).toHaveTextContent("Clé manquante pour ce niveau.");
    let launches = 0;
    server.use(
      http.post(`${API}/documents/d1/learned`, () => {
        launches += 1;
        return HttpResponse.json({ session_id: "s2" }, { status: 202 });
      }),
      http.get(`${API}/sessions/s2`, () =>
        HttpResponse.json({ ...sessionView("running"), id: "s2" }),
      ),
    );
    const progress = screen.getByRole("region", { name: /Archivist progress/ });
    await user.click(within(progress).getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(launches).toBe(1));
    await waitFor(() => expect(fake.sockets).toHaveLength(2));
    fake
      .last()
      .open()
      .push({ ...written(2, "Attention"), session_id: "s2" });
    fake.last().push({ ...completed(3), session_id: "s2" });
    expect(await screen.findByText("1 acquired skill(s) added")).toBeInTheDocument();
    useSessionStore.getState().reset("s2");
  });

  it("can relaunch a document already marked learned after a reload (I2)", async () => {
    const { backend, user } = setup({
      documents: [documentOut({ id: "d1", name: "Cours NLP", learned: true })],
    });
    let launches = 0;
    server.use(
      http.post(`${API}/documents/d1/learned`, () => {
        launches += 1;
        return HttpResponse.json({ session_id: "s1" }, { status: 202 });
      }),
    );
    expect(backend.documents).toHaveLength(1);
    expect(await screen.findByText("Marked as already learned")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(launches).toBe(1));
  });

  it("shows the server refusal when the document cannot be marked", async () => {
    const { user } = setup({ documents: [documentOut({ id: "d1" })] });
    server.use(
      http.post(`${API}/documents/d1/learned`, () =>
        apiError("document_not_indexed", "Le document n'est pas encore indexé.", 409),
      ),
    );
    await user.click(await screen.findByRole("button", { name: "Already learned" }));
    expect(await screen.findByText("Le document n'est pas encore indexé.")).toBeInTheDocument();
  });
});

describe("DocumentsPage after a reload", () => {
  beforeEach(() => {
    useSessionStore.getState().reset("s1");
    server.use(http.get(SESSION, () => HttpResponse.json(sessionView("running"))));
  });
  afterEach(() => useSessionStore.getState().reset("s1"));

  const documents = [documentOut({ id: "d1", name: "Cours NLP", learned: true })];

  it("follows a running Archiviste session again", async () => {
    const { fake } = setup({ documents, sessions: [sessionOut()] });
    expect(
      await screen.findByLabelText("Archivist progress for “Cours NLP”"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Already learned" })).toBeDisabled();
    await waitFor(() => expect(fake.sockets).toHaveLength(1));
    fake.last().open().push(started(1, "archivist"), written(2, "Attention"), completed(3));
    expect(await screen.findByText("1 acquired skill(s) added")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
  });

  it("ignores running sessions of other subjects", async () => {
    const { fake } = setup({
      documents,
      sessions: [sessionOut({ subject_type: "goal", subject_id: "g1" })],
    });
    expect(await screen.findByText("Cours NLP")).toBeInTheDocument();
    expect(screen.queryByLabelText(/Archivist progress/)).toBeNull();
    expect(fake.sockets).toHaveLength(0);
  });
});
