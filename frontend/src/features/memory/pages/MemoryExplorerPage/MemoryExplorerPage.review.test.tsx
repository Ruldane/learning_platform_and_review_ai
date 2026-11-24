import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { API, apiError, itemOut, memoryBackend, readHandlers, writeHandlers } from "../../fixtures";
import { MemoryExplorerPage } from "./MemoryExplorerPage";

function setup(initial = "/memory", init: Parameters<typeof memoryBackend>[0] = {}) {
  const backend = memoryBackend(init);
  server.use(...readHandlers(backend), ...writeHandlers(backend));
  const view = renderRoutes([{ path: "/memory", element: <MemoryExplorerPage /> }], initial);
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
  itemOut({ id: "l1", kind: "lesson", title: "Leçon A", level: null }),
  itemOut({ id: "l2", kind: "lesson", title: "Leçon B", level: null }),
];

describe("MemoryExplorerPage (final review fixes)", () => {
  it("does not show the save error of one item on the next item (I3)", async () => {
    const { user } = setup("/memory?item=i1");
    server.use(
      http.patch(`${API}/memory/items/:id`, () =>
        apiError("memory_duplicate", "Un élément identique existe déjà.", 409),
      ),
    );
    const drawer = await screen.findByRole("dialog");
    await user.click(await within(drawer).findByRole("button", { name: "Edit" }));
    await user.type(within(drawer).getByLabelText("Title"), " v2");
    await user.click(within(drawer).getByRole("button", { name: "Save" }));
    expect(await within(drawer).findByText("Un élément identique existe déjà.")).toBeVisible();
    await user.click(within(drawer).getByRole("button", { name: "Close" }));
    await user.click(await screen.findByRole("button", { name: "Backpropagation" }));
    const next = await screen.findByRole("dialog", { name: "Backpropagation" });
    expect(within(next).queryByText("Un élément identique existe déjà.")).not.toBeInTheDocument();
  });

  it("does not show the save error on the creation form either (I3)", async () => {
    const { user } = setup("/memory?item=i1");
    server.use(
      http.patch(`${API}/memory/items/:id`, () =>
        apiError("memory_duplicate", "Un élément identique existe déjà.", 409),
      ),
    );
    const drawer = await screen.findByRole("dialog");
    await user.click(await within(drawer).findByRole("button", { name: "Edit" }));
    await user.type(within(drawer).getByLabelText("Title"), " v2");
    await user.click(within(drawer).getByRole("button", { name: "Save" }));
    await within(drawer).findByText("Un élément identique existe déjà.");
    await user.click(screen.getByRole("button", { name: "Add" }));
    const form = await screen.findByRole("dialog", { name: "New item" });
    expect(within(form).queryByText("Un élément identique existe déjà.")).not.toBeInTheDocument();
  });

  it("falls back to the previous page when a delete empties the last one (I4)", async () => {
    const many = Array.from({ length: 26 }, (_, n) =>
      itemOut({ id: `m${n + 1}`, title: `Élément ${String(n + 1).padStart(2, "0")}` }),
    );
    const { backend, user } = setup("/memory", { items: many });
    paginate(backend);
    expect(await screen.findByText("Élément 01")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.click(await screen.findByRole("button", { name: "Élément 26" }));
    const drawer = await screen.findByRole("dialog", { name: "Élément 26" });
    await user.click(await within(drawer).findByRole("button", { name: "Delete" }));
    await user.click(within(drawer).getByRole("button", { name: "Yes, delete" }));
    expect(await screen.findByRole("button", { name: "Élément 01" })).toBeInTheDocument();
    expect(screen.queryByText("No items in memory")).not.toBeInTheDocument();
  });

  it("locks the merge while it is in flight and sends it once (I5)", async () => {
    const { backend, user } = setup("/memory", { items: lessons });
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
    await user.click(await screen.findByLabelText("Select “Leçon A”"));
    await user.click(screen.getByLabelText("Select “Leçon B”"));
    await user.click(screen.getByRole("button", { name: "Merge" }));
    await user.click(screen.getByRole("button", { name: "Yes, merge" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Merge" })).toBeDisabled());
    await user.click(screen.getByRole("button", { name: "Merge" }));
    release();
    await waitFor(() => expect(screen.queryByText("Leçon B")).not.toBeInTheDocument());
    expect(calls).toBe(1);
  });
});
