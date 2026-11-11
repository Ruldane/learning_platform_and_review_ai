import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/server";
import {
  API,
  apiError,
  itemOut,
  memoryBackend,
  readHandlers,
  statsOut,
  writeHandlers,
} from "../../fixtures";
import { renderRoutes } from "@/test/renderRoutes";
import { MemoryExplorerPage } from "./MemoryExplorerPage";

const DOCS = { path: "/memoire/documents", element: <p>Écran des documents</p> };

const pendingDecision = itemOut({
  id: "p1",
  kind: "decision",
  status: "pending",
  title: "Viser un poste NLP",
  level: null,
  reason: "Tu as lu trois offres NLP.",
});

function setup(initial = "/memoire", init: Parameters<typeof memoryBackend>[0] = {}) {
  const backend = memoryBackend(init);
  server.use(...readHandlers(backend), ...writeHandlers(backend));
  const view = renderRoutes([{ path: "/memoire", element: <MemoryExplorerPage /> }, DOCS], initial);
  return { backend, ...view };
}

describe("MemoryExplorerPage", () => {
  it("shows the stats, the search box and the items", async () => {
    setup();
    expect(await screen.findByText("Attention")).toBeInTheDocument();
    expect(screen.getByText("Backpropagation")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Éléments par type" })).toBeInTheDocument();
    expect(screen.getByLabelText("Requête")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Exporter en JSON" })).toHaveAttribute(
      "href",
      expect.stringMatching(/\/api\/v1\/memory\/export$/),
    );
    expect(screen.queryByRole("heading", { name: "À confirmer" })).not.toBeInTheDocument();
  });

  it("an agent write shows its author and reason in the drawer", async () => {
    const { user } = setup();
    await user.click(await screen.findByText("Attention"));
    const drawer = await screen.findByRole("dialog");
    expect(within(drawer).getAllByText("Archiviste").length).toBeGreaterThan(0);
    expect(
      within(drawer).getAllByText("Document « Cours NLP » marqué « déjà appris ».").length,
    ).toBeGreaterThan(0);
  });

  it("puts the opened item in the address and opens the item given in ?item=", async () => {
    const { router, user } = setup("/memoire?item=i3");
    const drawer = await screen.findByRole("dialog");
    expect(await within(drawer).findByText("Backpropagation")).toBeInTheDocument();
    await user.click(within(drawer).getByRole("button", { name: "Fermer" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(router.state.location.search).toBe("");
    await user.click(screen.getByText("Attention"));
    expect(router.state.location.search).toBe("?item=i1");
  });

  it("says so when the item in ?item= no longer exists, and lets the user close it", async () => {
    const { router, user } = setup("/memoire?item=zzz");
    expect(await screen.findByText("Élément introuvable.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fermer" }));
    expect(router.state.location.search).toBe("");
  });

  it("confirms a pending decision with PATCH status active, then hides the box", async () => {
    const { backend, user } = setup("/memoire", {
      items: [itemOut(), pendingDecision],
      stats: statsOut({ pending_decisions: 1 }),
    });
    expect(await screen.findByText("Viser un poste NLP")).toBeInTheDocument();
    expect(screen.getByText("Tu as lu trois offres NLP.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmer" }));
    await waitFor(() =>
      expect(backend.writes).toEqual([
        { method: "PATCH", path: "/memory/items/p1", body: { status: "active" } },
      ]),
    );
    await waitFor(() => expect(screen.queryByRole("button", { name: "Confirmer" })).toBeNull());
  });

  it("rejects a pending decision with DELETE", async () => {
    const { backend, user } = setup("/memoire", { items: [itemOut(), pendingDecision] });
    await user.click(await screen.findByRole("button", { name: "Refuser" }));
    await waitFor(() =>
      expect(backend.writes).toEqual([{ method: "DELETE", path: "/memory/items/p1", body: null }]),
    );
    await waitFor(() => expect(screen.queryByRole("button", { name: "Refuser" })).toBeNull());
  });

  it("a search finds the imported PDF with its score", async () => {
    const { backend, user } = setup();
    await user.type(await screen.findByLabelText("Requête"), "attention");
    await user.click(screen.getByRole("button", { name: "Rechercher" }));
    expect(await screen.findByText("0,83")).toBeInTheDocument();
    expect(backend.writes[0]?.body).toEqual({ query: "attention", kinds: null, k: 8 });
  });

  it("merges two selected items of the same kind", async () => {
    const lessons = [
      itemOut({ id: "l1", kind: "lecon", title: "Leçon A", level: null }),
      itemOut({ id: "l2", kind: "lecon", title: "Leçon B", level: null }),
    ];
    const { backend, user } = setup("/memoire", { items: lessons });
    await user.click(await screen.findByLabelText("Sélectionner « Leçon A »"));
    await user.click(screen.getByLabelText("Sélectionner « Leçon B »"));
    await user.click(screen.getByRole("button", { name: "Fusionner" }));
    await waitFor(() =>
      expect(backend.writes).toEqual([
        { method: "POST", path: "/memory/items/l1/merge", body: { other_ids: ["l2"] } },
      ]),
    );
    await waitFor(() => expect(screen.queryByText("Leçon B")).not.toBeInTheDocument());
  });

  it("shows the readable refusal when the merge is rejected", async () => {
    const lessons = [
      itemOut({ id: "l1", kind: "lecon", title: "Leçon A", level: null }),
      itemOut({ id: "l2", kind: "lecon", title: "Leçon B", level: null }),
    ];
    const { user } = setup("/memoire", { items: lessons });
    server.use(
      http.post(`${API}/memory/items/:id/merge`, () =>
        apiError("memory_duplicate", "Ce contenu existe déjà dans ta mémoire.", 409),
      ),
    );
    await user.click(await screen.findByLabelText("Sélectionner « Leçon A »"));
    await user.click(screen.getByLabelText("Sélectionner « Leçon B »"));
    await user.click(screen.getByRole("button", { name: "Fusionner" }));
    expect(await screen.findByText("Ce contenu existe déjà dans ta mémoire.")).toBeInTheDocument();
  });

  it("creates an item from the Ajouter button", async () => {
    const { backend, user } = setup();
    await user.click(await screen.findByRole("button", { name: "Ajouter" }));
    const drawer = await screen.findByRole("dialog");
    await user.type(within(drawer).getByLabelText("Titre"), "Softmax");
    await user.type(within(drawer).getByLabelText("Texte"), "Normalise les scores.");
    await user.click(within(drawer).getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(backend.writes[0]?.method).toBe("POST"));
    expect(backend.writes[0]?.body).toEqual(
      expect.objectContaining({ kind: "acquis", title: "Softmax", text: "Normalise les scores." }),
    );
  });

  it("asks for a reindex", async () => {
    const { backend, user } = setup();
    await user.click(await screen.findByRole("button", { name: "Réindexer" }));
    await waitFor(() => expect(backend.writes).toHaveLength(1));
    expect(backend.writes[0]?.path).toBe("/memory/reindex");
  });

  it("offers to import a document when the memory is empty", async () => {
    const { router, user } = setup("/memoire", { items: [] });
    expect(await screen.findByText("Aucun élément en mémoire")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Importer un document" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/memoire/documents"));
  });

  it("shows a retryable error when the list fails", async () => {
    const { backend, user } = setup();
    let calls = 0;
    server.use(
      http.get(`${API}/memory/items`, ({ request }) => {
        if (new URL(request.url).searchParams.get("status") === "pending") {
          return HttpResponse.json({ items: [], total: 0 });
        }
        calls += 1;
        if (calls === 1) return apiError("boom", "Panne de la liste.", 500);
        return HttpResponse.json({ items: backend.items, total: backend.items.length });
      }),
    );
    expect(await screen.findByText("Panne de la liste.")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Réessayer" })[0]!);
    expect(await screen.findByText("Attention")).toBeInTheDocument();
  });

  it("shows a loading state first", () => {
    setup();
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
  });

  it("edits the opened item with PATCH, then shows it read-only again", async () => {
    const { backend, user } = setup("/memoire?item=i1");
    const drawer = await screen.findByRole("dialog");
    await user.click(await within(drawer).findByRole("button", { name: "Modifier" }));
    const title = within(drawer).getByLabelText("Titre");
    await user.clear(title);
    await user.type(title, "Attention v2");
    await user.click(within(drawer).getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(backend.writes[0]?.method).toBe("PATCH"));
    expect(backend.writes[0]?.path).toBe("/memory/items/i1");
    expect(backend.writes[0]?.body).toEqual(expect.objectContaining({ title: "Attention v2" }));
    expect(await within(drawer).findByRole("button", { name: "Modifier" })).toBeInTheDocument();
  });

  it("deletes the opened item after an in-page confirmation, and closes the drawer", async () => {
    const { backend, router, user } = setup("/memoire?item=i1");
    const drawer = await screen.findByRole("dialog");
    await user.click(await within(drawer).findByRole("button", { name: "Supprimer" }));
    await user.click(within(drawer).getByRole("button", { name: "Oui, supprimer" }));
    await waitFor(() =>
      expect(backend.writes).toEqual([{ method: "DELETE", path: "/memory/items/i1", body: null }]),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(router.state.location.search).toBe("");
    expect(screen.queryByText("Élément introuvable.")).not.toBeInTheDocument();
  });
});
