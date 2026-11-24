/// <reference lib="dom" />

import { expect, test } from "@playwright/test";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

const lessonId = "relecture-e2e";
const published = {
  id: lessonId,
  module_id: "module-e2e",
  program_id: "programme-e2e",
  title: "Les messages de LangChain",
  week_rank: 1,
  status: "ready",
  attempts: 1,
  failure_reason: null,
  verification_failure_reason: null,
  markdown: "Une première version des messages.",
  word_count: 1400,
  pdf_available: true,
  done_tasks: 0,
  total_tasks: 3,
  completed: false,
  resources: [],
};

test.beforeEach(({ request }) => finishFirstLaunch(request));

test("le lecteur garde la version publiée pendant la vérification", async ({ page }) => {
  let verificationFinished = false;
  await page.route(`**/api/v1/lessons/${lessonId}`, (route) =>
    route.fulfill({
      json: verificationFinished
        ? {
            ...published,
            markdown: "La version vérifiée des messages.",
            verification_session_id: null,
          }
        : { ...published, verification_session_id: "verification-e2e" },
    }),
  );

  await page.goto(`/learn/lessons/${lessonId}`);
  const review = page.getByRole("status", { name: "À vérifier" });
  await expect(review).toBeVisible();
  await expect(page.getByText("Une première version des messages.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Télécharger le PDF" })).toBeVisible();

  verificationFinished = true;
  await expect(page.getByText("La version vérifiée des messages.")).toBeVisible();
  await expect(review).toHaveCount(0);
});

test("le professeur retrouve le fil de la leçon sans quitter le lecteur", async ({ page }) => {
  const lessonPath = `/learn/lessons/${lessonId}`;
  const conversationPath = `**/api/v1/lessons/${lessonId}/conversation`;
  const excerpt = "Une première version des messages.";
  const question = "À quoi sert un message système ?";
  const answer = "Il indique le rôle attendu du modèle.";
  let sent = false;
  await page.route(`**/api/v1/lessons/${lessonId}`, (route) => route.fulfill({ json: published }));
  await page.route(conversationPath, (route) =>
    route.fulfill({
      json: sent
        ? {
            id: "fil-e2e",
            lesson_id: lessonId,
            turns: [
              {
                id: "tour-e2e",
                request_id: "requete-e2e",
                session_id: "session-e2e",
                status: "completed",
                question,
                passage: excerpt,
                answer,
                sources: [{ kind: "memory", id: "fiche-e2e", title: "Les rôles", excerpt: null }],
              },
            ],
            usage: {
              thread_tokens: 37,
              thread_token_limit: 100_000,
              day_tokens: 37,
              day_token_limit: 300_000,
              turns: 1,
              turn_limit: 100,
            },
          }
        : null,
    }),
  );
  await page.route(`${conversationPath}/messages`, (route) => {
    expect(route.request().postDataJSON()).toMatchObject({
      question,
      passage: excerpt,
      passage_occurrence: 0,
      strong: false,
    });
    sent = true;
    return route.fulfill({ status: 202, json: { session_id: "session-e2e" } });
  });

  await page.goto(lessonPath);
  await page
    .getByTestId("lesson-body")
    .getByText(excerpt)
    .evaluate((paragraph) => {
      const range = document.createRange();
      range.selectNodeContents(paragraph);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
    });
  await page.getByRole("button", { name: "Demander au professeur", exact: true }).press("Enter");
  const panel = page.getByRole("dialog", { name: "Professeur" });
  await expect(panel.getByRole("heading", { name: "Professeur" })).toBeFocused();
  await expect(panel.getByText(excerpt)).toBeVisible();
  await expect(page).toHaveURL(new RegExp(`${lessonPath}$`));

  const input = panel.getByRole("textbox", { name: "Ta question" });
  await input.fill(question);
  await input.press("Enter");
  await expect(panel.getByText(answer)).toBeVisible();
  await expect(panel.getByRole("link", { name: "Les rôles" })).toHaveAttribute(
    "href",
    "/memory?item=fiche-e2e",
  );

  await input.press("Escape");
  await expect(panel).toHaveCount(0);
  const reopen = page.getByRole("button", { name: "Ouvrir la conversation avec le professeur" });
  await expect(reopen).toBeFocused();
  await reopen.press("Enter");
  await expect(panel.getByText(answer)).toBeVisible();
});
