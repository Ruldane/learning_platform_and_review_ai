import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

test("lit la transcription et répond aux trois questions quand l’audio est indisponible", async ({
  page,
  request,
}) => {
  await finishFirstLaunch(request);
  const episode = {
    id: "podcast-recette",
    day: "2026-11-22",
    lesson_id: "lecon",
    title: "Assembler une chaîne",
    status: "transcript",
    duration_seconds: null,
    lines: [
      { speaker: "host", text: "Que fait une chaîne ?" },
      { speaker: "coach", text: "Elle relie plusieurs opérations." },
    ],
    questions: ["Question A", "Question B", "Question C"].map((question) => ({
      question,
      choices: ["Une valeur", "Deux valeurs", "Trois valeurs"],
    })),
  };
  await page.route("**/api/v1/podcast/today", (route) => route.fulfill({ json: episode }));
  await page.route("**/api/v1/podcast/podcast-recette/quiz", (route) => {
    expect(route.request().postDataJSON()).toEqual({ choices: [1, 1, 1] });
    const corrections = episode.questions.map(() => ({
      answer: 1,
      correct: true,
      explanation: "Les deux valeurs sont gardées.",
    }));
    return route.fulfill({ json: { score: 3, corrections } });
  });
  await page.goto("/etudier/podcast");
  await expect(page.getByRole("heading", { name: episode.title })).toBeVisible();
  await expect(page.getByText("La transcription et les questions sont disponibles.")).toBeVisible();
  await expect(page.getByText("Elle relie plusieurs opérations.", { exact: false })).toBeVisible();
  for (const question of episode.questions) {
    await page
      .getByRole("group", { name: question.question })
      .getByRole("radio", { name: "Deux valeurs" })
      .check();
  }
  await page.getByRole("button", { name: "Vérifier mes réponses" }).click();
  await expect(
    page.getByRole("status").filter({ hasText: "3 réponses correctes sur 3" }),
  ).toBeVisible();
});
