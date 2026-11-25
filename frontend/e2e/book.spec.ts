import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

const api = process.env.E2E_API_URL ?? "http://localhost:8765";

test("Ton livre prépare une édition et télécharge le PDF et l’EPUB", async ({ page, request }) => {
  await finishFirstLaunch(request);
  const seeded = await request.post(`${api}/__e2e/book/seed`);
  expect(seeded.ok()).toBeTruthy();
  const { program_id: programId } = (await seeded.json()) as { program_id: string };
  await page.goto("/learn/book");
  await page.getByRole("combobox", { name: "Programme" }).selectOption(programId);

  const prepare = page.getByRole("button", { name: "Préparer le livre" });
  await prepare.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("L’édition est en préparation.")).toBeVisible();
  expect((await request.post(`${api}/__e2e/book/refresh`)).ok()).toBeTruthy();

  const pdf = page.getByRole("link", { name: "Télécharger en PDF" });
  await expect(pdf).toBeFocused();
  await expect(page.getByText("Chapitres publiés dans l’édition : 1")).toBeVisible();
  const [pdfFile] = await Promise.all([page.waitForEvent("download"), pdf.click()]);
  expect(pdfFile.suggestedFilename()).toBe("ton-livre.pdf");
  const pdfBytes = await readFile(await pdfFile.path());
  expect(pdfBytes.subarray(0, 5).toString("ascii")).toBe("%PDF-");

  const epub = page.getByRole("link", { name: "Télécharger en EPUB" });
  const [epubFile] = await Promise.all([page.waitForEvent("download"), epub.click()]);
  expect(epubFile.suggestedFilename()).toBe("ton-livre.epub");
  const epubBytes = await readFile(await epubFile.path());
  expect(epubBytes.subarray(0, 4).toString("hex")).toBe("504b0304");
  expect(epubBytes.includes(Buffer.from("application/epub+zip"))).toBeTruthy();
});
