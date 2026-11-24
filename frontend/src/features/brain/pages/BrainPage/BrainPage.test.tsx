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
    expect(await screen.findByText("Sync relay needs to be configured")).toBeVisible();
    const connection = screen.getByRole("complementary", { name: "Relay status" });
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
    await user.type(await screen.findByRole("textbox", { name: "Folder name" }), "Cours");
    await user.type(screen.getByRole("textbox", { name: "Folder path" }), "C:\\Notes");
    await user.click(screen.getByRole("button", { name: "Add folder" }));
    const card = await screen.findByRole("article", { name: "Cours" });
    expect(within(card).getByText("C:\\Notes")).toBeVisible();
    expect(within(card).getByText("2 of 3 indexed")).toBeVisible();
    await user.click(within(card).getByText("Last pass summary"));
    expect(within(card).getByText("Binary files", { exact: false })).toBeVisible();
    await user.click(within(card).getByRole("button", { name: "Pause" }));
    expect(await within(card).findByRole("button", { name: "Resume" })).toBeVisible();
  });

  it("confirms removal and returns focus to the folder form", async () => {
    server.use(http.get(`${base}/folders`, () => HttpResponse.json([folder])));
    server.use(http.get(`${base}/status`, () => HttpResponse.json([])));
    server.use(http.delete(`${base}/folders/notes`, () => new HttpResponse(null, { status: 204 })));
    const { user } = setup();
    const card = await screen.findByRole("article", { name: "Cours" });
    await user.click(within(card).getByRole("button", { name: "Remove folder" }));
    const dialog = screen.getByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: "Remove folder" }));
    expect(await screen.findByText("No synced folders.")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Folder name" })).toHaveFocus();
  });
});
