import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import type { components } from "../src/shared/api/schema.d.ts";
import { API, finishFirstLaunch } from "./support/firstLaunch.ts";

test.skip(
  process.env.E2E_PODCAST_INTEGRATION !== "1",
  "Requiert le serveur synthétique tests.e2e.podcast_integration.",
);

const episodeTitle = "Composer des chaînes de traitement";
const transcript = "Une chaîne relie plusieurs étapes.";
const choices = [
  ["Par quoi commence la chaîne ?", "Une entrée", "Le premier maillon reçoit l’entrée."],
  [
    "Que transmet le premier maillon ?",
    "Sa durée",
    "Le résultat devient l’entrée du maillon suivant.",
  ],
  [
    "Comment contrôler le résultat ?",
    "Comparer avec la sortie attendue",
    "La sortie attendue sert de repère.",
  ],
] as const;

async function readAudioMetadata(player: Locator, expectedSeconds: number) {
  const capable = await player.evaluate(
    (element) => element instanceof HTMLAudioElement && Boolean(element.canPlayType("audio/wav")),
  );
  if (!capable) return;
  await player.evaluate((element) => {
    if (!(element instanceof HTMLAudioElement)) throw new Error("Lecteur audio absent.");
    element.preload = "metadata";
    element.load();
  });
  await expect
    .poll(() =>
      player.evaluate((element) =>
        element instanceof HTMLAudioElement ? Math.round(element.duration) : 0,
      ),
    )
    .toBe(expectedSeconds);
}

async function verifyAudio(page: Page, request: APIRequestContext) {
  const player = page.locator('audio[aria-label="Écouter l’épisode"]');
  await expect(player).toBeVisible({ timeout: 30_000 });
  const episodeResponse = await request.get(API + "/podcast/today");
  expect(episodeResponse.ok()).toBe(true);
  const episode = (await episodeResponse.json()) as components["schemas"]["PodcastEpisodeOut"];
  expect(episode.status).toBe("ready");
  expect(episode.duration_seconds).toBe(610);
  const wavUrl = API + "/podcast/" + episode.id + "/audio";
  await expect(player).toHaveAttribute("src", wavUrl);
  const wav = await request.get(wavUrl);
  expect(wav.ok()).toBe(true);
  expect(wav.headers()["content-type"]).toContain("audio/wav");
  expect((await wav.body()).subarray(0, 12).toString("ascii")).toMatch(/^RIFF....WAVE$/s);
  await readAudioMetadata(player, 610);
  return { player, wavUrl, id: episode.id };
}

async function verifyQuiz(page: Page, id: string) {
  for (const [question, answer] of choices) {
    await page.getByRole("group", { name: question }).getByRole("radio", { name: answer }).check();
  }
  const correction = page.waitForResponse(
    (response) =>
      response.url() === API + "/podcast/" + id + "/quiz" && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Vérifier mes réponses" }).press("Enter");
  expect((await correction).ok()).toBe(true);
  await expect(
    page.getByRole("status").filter({ hasText: "2 réponses correctes sur 3" }),
  ).toBeVisible();
  for (const [question, , explanation] of choices) {
    await expect(
      page.getByRole("group", { name: question }).getByText(explanation, { exact: false }),
    ).toBeVisible();
  }
}

test("prépare le podcast, corrige le quiz et relit le même épisode", async ({ page, request }) => {
  await finishFirstLaunch(request);
  await page.goto("/etudier/podcast", { waitUntil: "domcontentloaded" });
  const preparing = page.waitForResponse(
    (response) =>
      response.url() === API + "/podcast/today" && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Préparer l’épisode du jour" }).press("Enter");
  expect((await preparing).status()).toBe(202);
  await expect(page.getByRole("heading", { name: episodeTitle })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Transcription" })).toBeVisible();
  await expect(page.getByText(transcript, { exact: false }).first()).toBeVisible();

  const { player, wavUrl, id } = await verifyAudio(page, request);

  await verifyQuiz(page, id);

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: episodeTitle })).toBeVisible();
  await expect(page.getByText(transcript, { exact: false }).first()).toBeVisible();
  await expect(player).toHaveAttribute("src", wavUrl);
  for (const [question] of choices)
    await expect(page.getByRole("group", { name: question })).toBeVisible();
});
