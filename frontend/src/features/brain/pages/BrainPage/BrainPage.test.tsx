import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import { renderRoutes } from "@/test/renderRoutes";
import { server } from "@/test/server";
import { BrainPage } from "./BrainPage";

const base = "http://localhost:8000/api/v1/brain";
const folder = { id: "notes", name: "Cours", path: "C:\\Notes", paused: false, revision: 1 };

function setup() {
  return renderRoutes([{ path: "/memory/brain", element: <BrainPage /> }], "/memory/brain");
}

describe("BrainPage", () => {
  beforeEach(() => {
    server.use(http.get(`${base}/relay`, () => HttpResponse.json({ state: "unconfigured" })));
  });

  it("explains an unconfigured relay on an empty account", async () => {
    server.use(http.get(`${base}/folders`, () => HttpResponse.json([])));
    server.use(http.get(`${base}/status`, () => HttpResponse.json([])));
    setup();
    expect(await screen.findByText("Relais de synchronisation à configurer")).toBeVisible();
    const connection = screen.getByRole("complementary", { name: "État du relais" });
    expect(within(connection).getByText(/TREMPLIN_BRAIN_SYNC_TOKEN/)).toBeVisible();
  });

  it("registers a folder, shows import counts, and can pause the sync", async () => {
    server.use(http.get(`${base}/folders`, () => HttpResponse.json([])));
    server.use(
      http.get(`${base}/status`, () =>
        HttpResponse.json([
          {
            id: folder.id,
            name: folder.name,
            paused: false,
            revision: 1,
            total: 3,
            queued: 1,
            processing: 0,
            indexed: 2,
            error: 0,
            report: {
              state: "done",
              scanned: 3,
              added: 3,
              changed: 0,
              removed: 0,
              ignored: { binary: 1 },
              errors: 0,
              reported_at: "2026-11-22T07:00:00Z",
            },
          },
        ]),
      ),
    );
    server.use(
      http.post(`${base}/folders`, async ({ request }) => {
        expect(await request.json()).toMatchObject({ name: "Cours", path: "C:\\Notes" });
        return HttpResponse.json(folder, { status: 201 });
      }),
    );
    server.use(
      http.patch(`${base}/folders/notes`, async ({ request }) => {
        expect(await request.json()).toMatchObject({ paused: true });
        return HttpResponse.json({ ...folder, paused: true, revision: 2 });
      }),
    );
    const { user } = setup();
    await user.type(await screen.findByRole("textbox", { name: "Nom du dossier" }), "Cours");
    await user.type(screen.getByRole("textbox", { name: "Chemin du dossier" }), "C:\\Notes");
    await user.click(screen.getByRole("button", { name: "Ajouter le dossier" }));
    const card = await screen.findByRole("article", { name: "Cours" });
    expect(within(card).getByText("C:\\Notes")).toBeVisible();
    expect(within(card).getByText("2 indexés sur 3")).toBeVisible();
    await user.click(within(card).getByText("Bilan du dernier passage"));
    expect(within(card).getByText("Fichiers binaires", { exact: false })).toBeVisible();
    await user.click(within(card).getByRole("button", { name: "Mettre en pause" }));
    expect(await within(card).findByRole("button", { name: "Reprendre" })).toBeVisible();
  });

  it("confirms removal and returns focus to the folder form", async () => {
    server.use(http.get(`${base}/folders`, () => HttpResponse.json([folder])));
    server.use(http.get(`${base}/status`, () => HttpResponse.json([])));
    server.use(http.delete(`${base}/folders/notes`, () => new HttpResponse(null, { status: 204 })));
    const { user } = setup();
    const card = await screen.findByRole("article", { name: "Cours" });
    await user.click(within(card).getByRole("button", { name: "Retirer le dossier" }));
    const dialog = screen.getByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: "Retirer le dossier" }));
    expect(await screen.findByText("Aucun dossier synchronisé.")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Nom du dossier" })).toHaveFocus();
  });
});
