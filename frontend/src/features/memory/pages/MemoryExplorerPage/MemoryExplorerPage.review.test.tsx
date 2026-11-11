import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { API, apiError, itemOut, memoryBackend, readHandlers, writeHandlers } from "../../fixtures";
import { MemoryExplorerPage } from "./MemoryExplorerPage";

function setup(initial = "/memoire", init: Parameters<typeof memoryBackend>[0] = {}) {
  const backend = memoryBackend(init);
  server.use(...readHandlers(backend), ...writeHandlers(backend));
  const view = renderRoutes([{ path: "/memoire", element: <MemoryExplorerPage /> }], initial);
  return { backend, ...view };
}

/** La liste du faux back, avec le décalage et la taille de page du vrai. */
function paginate(backend: ReturnType<typeof memoryBackend>) {
  server.use(
    http.get(`${API}/memory/items`, ({ request }) => {
      const q = new URL(request.url).searchParams;
      const all = backend.items.filter((i) => i.status === (q.get("status") ?? "active"));
      const offset = Number(q.get("offset") ?? 0);
      const limit = Number(q.get("limit") ?? 25);
      return HttpResponse.json({ items: all.slice(offset, offset + limit), total: all.length });
    }),
  );
}

const lessons = [
  itemOut({ id: "l1", kind: "lecon", title: "Leçon A", level: null }),
  itemOut({ id: "l2", kind: "lecon", title: "Leçon B", level: null }),
];

describe("MemoryExplorerPage (final review fixes)", () => {
  it("does not show the save error of one item on the next item (I3)", async () => {
    const { user } = setup("/memoire?item=i1");
    server.use(
      http.patch(`${API}/memory/items/:id`, () =>
        apiError("memory_duplicate", "Un élément identique existe déjà.", 409),
      ),
    );
    const drawer = await screen.findByRole("dialog");
    await user.click(await within(drawer).findByRole("button", { name: "Modifier" }));
    await user.type(within(drawer).getByLabelText("Titre"), " v2");
    await user.click(within(drawer).getByRole("button", { name: "Enregistrer" }));
    expect(await within(drawer).findByText("Un élément identique existe déjà.")).toBeVisible();
    await user.click(within(drawer).getByRole("button", { name: "Fermer" }));
    await user.click(await screen.findByRole("button", { name: "Backpropagation" }));
    const next = await screen.findByRole("dialog", { name: "Backpropagation" });
    expect(within(next).queryByText("Un élément identique existe déjà.")).not.toBeInTheDocument();
  });

  it("does not show the save error on the creation form either (I3)", async () => {
    const { user } = setup("/memoire?item=i1");
    server.use(
      http.patch(`${API}/memory/items/:id`, () =>
        apiError("memory_duplicate", "Un élément identique existe déjà.", 409),
      ),
    );
    const drawer = await screen.findByRole("dialog");
    await user.click(await within(drawer).findByRole("button", { name: "Modifier" }));
    await user.type(within(drawer).getByLabelText("Titre"), " v2");
    await user.click(within(drawer).getByRole("button", { name: "Enregistrer" }));
    await within(drawer).findByText("Un élément identique existe déjà.");
    await user.click(screen.getByRole("button", { name: "Ajouter" }));
    const form = await screen.findByRole("dialog", { name: "Nouvel élément" });
    expect(within(form).queryByText("Un élément identique existe déjà.")).not.toBeInTheDocument();
  });

  it("falls back to the previous page when a delete empties the last one (I4)", async () => {
    const many = Array.from({ length: 26 }, (_, n) =>
      itemOut({ id: `m${n + 1}`, title: `Élément ${String(n + 1).padStart(2, "0")}` }),
    );
    const { backend, user } = setup("/memoire", { items: many });
    paginate(backend);
    expect(await screen.findByText("Élément 01")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Suivant" }));
    await user.click(await screen.findByRole("button", { name: "Élément 26" }));
    const drawer = await screen.findByRole("dialog", { name: "Élément 26" });
    await user.click(await within(drawer).findByRole("button", { name: "Supprimer" }));
    await user.click(within(drawer).getByRole("button", { name: "Oui, supprimer" }));
    expect(await screen.findByRole("button", { name: "Élément 01" })).toBeInTheDocument();
    expect(screen.queryByText("Aucun élément en mémoire")).not.toBeInTheDocument();
  });

  it("locks the merge while it is in flight and sends it once (I5)", async () => {
    const { backend, user } = setup("/memoire", { items: lessons });
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    let calls = 0;
    server.use(
      http.post(`${API}/memory/items/:id/merge`, async () => {
        calls += 1;
        await gate;
        backend.items = backend.items.filter((i) => i.id !== "l2");
        return HttpResponse.json(backend.items[0]);
      }),
    );
    await user.click(await screen.findByLabelText("Sélectionner « Leçon A »"));
    await user.click(screen.getByLabelText("Sélectionner « Leçon B »"));
    await user.click(screen.getByRole("button", { name: "Fusionner" }));
    await user.click(screen.getByRole("button", { name: "Oui, fusionner" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Fusionner" })).toBeDisabled());
    await user.click(screen.getByRole("button", { name: "Fusionner" }));
    release();
    await waitFor(() => expect(screen.queryByText("Leçon B")).not.toBeInTheDocument());
    expect(calls).toBe(1);
  });
});
