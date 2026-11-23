import { createHash } from "node:crypto";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

const filename = "calendrier.md";
const title = "Calendrier turquoise";
const contents = Buffer.from(
  "---\ntitle: Calendrier turquoise\n---\n\nLe calendrier turquoise indique le code TX-482-B.\n",
);

async function syncNote(request: APIRequestContext) {
  const folder = await request.post(`${API}/brain/folders`, {
    data: { name: "Notes de recette", path: "C:\\NotesTremplinRecette" },
  });
  expect(folder.ok()).toBe(true);
  const { id, revision } = (await folder.json()) as { id: string; revision: number };
  const auth = await request.post(`${API}/brain/sync-token`);
  expect(auth.ok()).toBe(true);
  const { token } = (await auth.json()) as { token: string };
  const headers = {
    Authorization: `Bearer ${token}`,
    "X-Tremplin-Folder-Revision": String(revision),
  };
  const endpoint = `${API}/brain/sync/folders/${id}`;
  const upload = await request.post(`${endpoint}/files`, {
    headers,
    multipart: {
      path: filename,
      sha256: createHash("sha256").update(contents).digest("hex"),
      file: { name: filename, mimeType: "text/markdown", buffer: contents },
    },
  });
  expect(upload.ok()).toBe(true);
  await expect
    .poll(async () => {
      const status = await request.get(`${API}/brain/status`);
      expect(status.ok()).toBe(true);
      const folders = (await status.json()) as { id: string; indexed: number }[];
      return folders.find((folder) => folder.id === id)?.indexed;
    })
    .toBe(1);
  return { endpoint, headers };
}

test.beforeEach(({ request }) => finishFirstLaunch(request));

test("le Cerveau cite une note synchronisée puis l’écarte après son retrait", async ({
  page,
  request,
}, testInfo) => {
  const { endpoint, headers } = await syncNote(request);
  const question = "Calendrier turquoise";
  await page.goto("/memoire/cerveau");
  const field = page.getByRole("textbox", { name: "Ta question au Cerveau" });
  await expect(
    page.getByRole("log", { name: "Conversation avec le bibliothécaire" }),
  ).toBeVisible();
  await field.fill(question);
  await field.press("Enter");
  await expect(page.getByText(/La note indique le code TX-482-B/)).toBeVisible();
  await page.getByRole("link", { name: title }).click();
  await expect(page).toHaveURL(/\/memoire\?item=[0-9a-f-]+$/);
  await expect(page.getByRole("dialog").getByRole("heading", { name: title })).toBeVisible();
  await expect(
    page
      .getByRole("dialog")
      .getByText(/Le calendrier turquoise indique le code/)
      .first(),
  ).toBeVisible();

  const removed = await request.post(`${endpoint}/remove`, { headers, data: { path: filename } });
  expect(removed.status()).toBe(204);
  await page.goto("/memoire/cerveau");
  await expect(
    page.getByRole("log", { name: "Conversation avec le bibliothécaire" }),
  ).toBeVisible();
  await field.fill(question);
  await field.press("Enter");
  const answer = page
    .getByRole("article", { name: "Bibliothécaire" })
    .filter({ hasText: "Je ne retrouve plus la note du calendrier." });
  await expect(answer).toBeVisible();
  await expect(answer.getByRole("link", { name: title })).toHaveCount(0);

  const sidebar = page.getByRole("complementary", { name: "Conversations" });
  await expect(sidebar.getByRole("button", { name: "Ouvrir Calendrier turquoise" })).toBeVisible();
  await sidebar.getByRole("button", { name: "Nouvelle conversation", exact: true }).click();
  await expect(page).toHaveURL(/conversation=[0-9a-f-]+$/);
  await expect(answer).toHaveCount(0);
  await expect(sidebar.getByRole("button", { name: "Ouvrir Nouvelle conversation" })).toBeVisible();
  await sidebar.getByRole("button", { name: "Ouvrir Calendrier turquoise" }).click();
  await expect(answer).toBeVisible();
  const search = sidebar.getByRole("searchbox", { name: "Rechercher un titre" });
  const draft = "Un brouillon conserve sa place.";
  await field.fill(draft);
  await search.fill("autre conversation");
  await expect(sidebar.getByText("Aucun titre ne correspond.")).toBeVisible();
  await expect(field).toHaveValue(draft);
  await expect(answer).toBeVisible();
  await search.clear();
  await expect(sidebar.getByRole("button", { name: "Ouvrir Calendrier turquoise" })).toBeVisible();
  await field.clear();
  await page.screenshot({ path: testInfo.outputPath("brain-conversations.png") });
  await sidebar.getByRole("button", { name: "Vider la conversation" }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Confirmer" }).click();
  await expect(answer).toHaveCount(0);
  await expect(sidebar.getByRole("button", { name: "Ouvrir Calendrier turquoise" })).toBeVisible();
});
