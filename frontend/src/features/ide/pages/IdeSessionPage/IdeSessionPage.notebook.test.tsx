import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { errorBody } from "@/test/authApi";
import { API } from "@/test/councilApi";
import { progress } from "@/test/ideApi";
import { findEditor, renderSession } from "../../ideTestkit";

it("ouvre une cellule sauvegardée et lance sa version éditée", async () => {
  const path = "atelier.ipynb";
  const root = `${API}/ide/sessions/s1/notebook`;
  const calls: unknown[] = [];
  const cell = { id: "a", kind: "code", source: "print(1)", output: null };
  const { user } = renderSession({
    session: {
      files: { "main.py": "", [path]: "{}" },
      tabs: { open_paths: [path], active_path: path },
    },
    override: [
      http.get(root, () => HttpResponse.json({ path, files_version: 4, cells: [cell] })),
      http.put(root, async ({ request }) => {
        calls.push(await request.json());
        return HttpResponse.json({
          path,
          files_version: 5,
          cells: [{ ...cell, source: "print(2)" }],
        });
      }),
      http.post(`${root}/run`, async ({ request }) => {
        calls.push(await request.json());
        return HttpResponse.json({ id: "n1" }, { status: 202 });
      }),
      http.get(`${API}/ide/notebook-runs/n1`, () =>
        HttpResponse.json(progress({ id: "n1", output: "2\n", next_offset: 2 })),
      ),
    ],
  });
  const source = await screen.findByRole("textbox", { name: "Source of cell 1" });
  expect(source).toHaveValue("print(1)");
  await user.clear(source);
  await user.type(source, "print(2)");
  await user.click(screen.getByRole("button", { name: "Run cell 1" }));
  await waitFor(() =>
    expect(calls).toEqual([
      { path, version: 4, cells: [{ id: "a", kind: "code", source: "print(2)" }] },
      { path, cell_id: "a", include_previous: false },
    ]),
  );
  await waitFor(() =>
    expect(screen.getByRole("log", { name: "Cell output" })).toHaveTextContent("2"),
  );
});

it("garde le brouillon de la cellule et sa version après un changement d’onglet", async () => {
  const path = "atelier.ipynb";
  const root = `${API}/ide/sessions/s1/notebook`;
  const sourceName = "Source of cell 1";
  const cell = { id: "a", kind: "code", source: "print(1)", output: null };
  const reads: number[] = [];
  const writes: unknown[] = [];
  let version = 4;
  const { user } = renderSession({
    session: {
      files: { "main.py": "", [path]: "{}" },
      tabs: { open_paths: ["main.py", path], active_path: path },
    },
    override: [
      http.put(
        `${API}/ide/sessions/s1/tabs`,
        async ({ request }) =>
          new HttpResponse(await request.text(), {
            headers: { "Content-Type": "application/json" },
          }),
      ),
      http.get(root, () => {
        reads.push(version);
        return HttpResponse.json({
          path,
          files_version: version,
          cells: [{ ...cell, source: version === 4 ? cell.source : "print(3)" }],
        });
      }),
      http.put(root, async ({ request }) => {
        writes.push(await request.json());
        return HttpResponse.json(errorBody("ide_files_conflict", "Le fichier a changé."), {
          status: 409,
        });
      }),
    ],
  });
  const source = await screen.findByRole("textbox", { name: sourceName });
  await user.clear(source);
  await user.type(source, "print(2)");
  const tabs = within(screen.getByRole("navigation", { name: "Session files" }));
  await user.click(tabs.getByRole("button", { name: /^main\.py/ }));
  await findEditor();
  version = 5;
  await user.click(tabs.getByRole("button", { name: path }));
  await waitFor(() => expect(reads).toContain(5));
  expect(await screen.findByRole("textbox", { name: sourceName })).toHaveValue("print(2)");
  await user.click(screen.getByRole("button", { name: "Save notebook" }));
  expect(await screen.findByText("Le fichier a changé.")).toBeVisible();
  expect(writes).toEqual([
    { path, version: 4, cells: [{ id: "a", kind: "code", source: "print(2)" }] },
  ]);
  expect(screen.getByRole("textbox", { name: sourceName })).toHaveValue("print(2)");
});
