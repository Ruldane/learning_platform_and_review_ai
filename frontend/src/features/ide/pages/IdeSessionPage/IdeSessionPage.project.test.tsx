import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { API } from "@/test/councilApi";
import { sessionOut } from "@/test/ideApi";
import { findEditor, renderSession } from "../../ideTestkit";

it("rouvre le dernier onglet choisi et ouvre un nouveau fichier créé", async () => {
  const files = { "main.py": "print('bonjour')", "src/util.py": "value = 3" };
  const tabs = { open_paths: ["main.py", "src/util.py"], active_path: "src/util.py" };
  const writes: unknown[] = [];
  const { user } = renderSession({
    session: { files, tabs, files_version: 5 },
    override: [
      http.post(`${API}/ide/sessions/s1/files`, async ({ request }) => {
        writes.push(await request.json());
        return HttpResponse.json(
          sessionOut({ files: { ...files, "src/extra.py": "" }, tabs, files_version: 6 }),
          { status: 201 },
        );
      }),
      http.put(`${API}/ide/sessions/s1/tabs`, async ({ request }) => {
        const body: unknown = await request.json();
        writes.push(body);
        return new HttpResponse(JSON.stringify(body), {
          headers: { "Content-Type": "application/json" },
        });
      }),
    ],
  });

  expect(await findEditor()).toHaveValue("value = 3");
  await user.click(screen.getByRole("button", { name: "Nouveau fichier" }));
  await user.type(screen.getByRole("textbox", { name: "Chemin du fichier" }), "src/extra.py");
  await user.click(screen.getByRole("button", { name: "Ajouter le fichier" }));

  await waitFor(() =>
    expect(writes).toEqual([
      { path: "src/extra.py", version: 5, content: "" },
      { open_paths: ["main.py", "src/util.py", "src/extra.py"], active_path: "src/extra.py" },
    ]),
  );
  expect(await findEditor()).toHaveValue("");
});
