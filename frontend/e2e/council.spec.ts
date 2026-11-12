import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";

/**
 * Parcours de bout en bout n° 1, « conseil complet » (SPEC 18.2), contre le serveur de bout en
 * bout (`tests.e2e.server`) : les réponses des agents sont scriptées (`council_script.py`), tout
 * le reste est l'application réelle. Les compteurs (8 sources retenues, 12 prises de parole,
 * 2 propositions, 2 leçons) sont ceux du script.
 */
const GOAL = "Devenir AI product engineer";
const FRAMING_ANSWER = "Huit heures par semaine, surtout le soir.";
const MESSAGE = "Je préfère un projet concret dès la première semaine.";
const DEBATERS = ["Stratège", "Praticien", "Éclaireur", "Sceptique"];
const ROUNDS = 3;
const SPEECH = /je donne ma position|je réponds au Conseil/;
const MOVED_TASK = "Regarder une démonstration d'appel";

function debateTurns(page: Page): Locator {
  return page.getByRole("list", { name: "Fil du débat" }).getByRole("article").filter({
    hasText: SPEECH,
  });
}

/** Objectif saisi, cadrage répondu, un message envoyé pendant le tour 1. */
async function openCouncil(page: Page): Promise<void> {
  await page.goto("/apprendre/objectifs");
  await page.getByRole("textbox", { name: "Ce que tu veux apprendre ou atteindre" }).fill(GOAL);
  await page.getByRole("button", { name: "Convoquer le Conseil" }).click();
  await expect(page).toHaveURL(/\/apprendre\/objectifs\/[^/]+\/conseil$/);

  const framing = page.getByRole("region", { name: /Réponds aux questions de cadrage/ });
  await framing.getByRole("textbox").first().fill(FRAMING_ANSWER);
  await framing.getByRole("button", { name: "Répondre" }).click();

  // Les prises de parole sont espacées par le serveur : le message part pendant le tour 1.
  await expect(debateTurns(page).first()).toBeVisible({ timeout: 60_000 });
  await page.getByRole("textbox", { name: "Ton message" }).fill(MESSAGE);
  await page.getByRole("button", { name: "Envoyer" }).click();
  await expect(page.getByRole("list", { name: "Fil du débat" }).getByText(MESSAGE)).toBeVisible();
}

/** 12 bulles (4 débatteurs × 3 tours) ; January n'est nommée qu'après son message. */
async function checkDebate(page: Page): Promise<void> {
  const turns = debateTurns(page);
  await expect(turns).toHaveCount(DEBATERS.length * ROUNDS);
  const feed = page.getByRole("list", { name: "Fil du débat" });
  for (const name of DEBATERS) {
    const spoken = feed.getByRole("article", { name, exact: true }).filter({ hasText: SPEECH });
    await expect(spoken).toHaveCount(ROUNDS);
  }
  const positions = turns.filter({ hasText: "je donne ma position" });
  await expect(positions).toHaveCount(DEBATERS.length);
  await expect(positions.filter({ hasText: "January" })).toHaveCount(0);
  const answers = turns.filter({ hasText: "je réponds au Conseil" }).filter({ hasText: "January" });
  expect(await answers.count()).toBeGreaterThan(0);
}

/** Sources retenues, tableau dessiné, deux propositions, puis le choix de la première. */
async function checkBoardAndChoose(page: Page): Promise<void> {
  await page.getByRole("tab", { name: "Sources" }).click();
  const kept = page.getByRole("region", { name: "Retenues" });
  await expect(kept.getByRole("listitem")).toHaveCount(8);
  // Chaque source retenue porte sa note (« 82/100 ») : le libellé est sur un élément générique.
  await expect(kept.getByText(/^\d{1,3}\/100$/)).toHaveCount(8);

  await page.getByRole("tab", { name: "Tableau" }).click();
  const canvas = page.getByRole("region", { name: /^Canevas du tableau/ }).locator("canvas");
  const fallback = page.getByText(/schéma simplifié/);
  await expect(canvas.first().or(fallback)).toBeVisible();

  await page.getByRole("tab", { name: "Propositions" }).click();
  const proposals = page.getByRole("tabpanel", { name: "Propositions" }).getByRole("article");
  await expect(proposals).toHaveCount(2);
  await page.getByRole("button", { name: /^Choisir « / }).first().click();
  await page.getByRole("link", { name: /^Voir le programme/ }).first().click();
  await expect(page).toHaveURL(/\/apprendre\/programme\/[^/]+$/);
}

/** Une tâche déplacée au clavier vers le mercredi (deuxième jour proposé : lundi est plein). */
async function moveTaskWithKeyboard(page: Page): Promise<void> {
  await expect(page.getByRole("button", { name: "Valider le programme" })).toBeVisible({
    timeout: 60_000,
  });
  const move = page.getByRole("button", { name: `Déplacer « ${MOVED_TASK} »` });
  await move.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("menu", { name: "Déplacer vers…" })).toBeVisible();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  const wednesday = page.getByRole("group", { name: /^mer\./ });
  await expect(wednesday.getByText(MOVED_TASK, { exact: true })).toBeVisible();
}

/** « 2 h 50 », « 45 min », « 11 h » → minutes. */
function minutes(text: string): number {
  const hours = /(\d+)\s*h(?:\s*(\d+))?/.exec(text);
  if (hours) return Number(hours[1]) * 60 + Number(hours[2] ?? 0);
  const only = /(\d+)\s*min/.exec(text);
  return only ? Number(only[1]) : Number.NaN;
}

/** Chaque semaine affiche une charge sous son plafond de 85 %. */
async function checkWeeklyLoad(page: Page): Promise<void> {
  const weeks = page.getByRole("combobox", { name: "Semaine affichée" });
  const count = await weeks.locator("option").count();
  expect(count).toBeGreaterThan(0);
  for (let index = 0; index < count; index += 1) {
    await weeks.selectOption({ index });
    await expect(page.getByText("Dans le plafond de la semaine.")).toBeVisible();
    const value = await page.getByText(/ \/ .*\(85 %\)$/).textContent();
    const [load = "", cap = ""] = (value ?? "").replace("(85 %)", "").split(" / ");
    expect(minutes(load)).toBeLessThanOrEqual(minutes(cap));
  }
}

/** Les leçons des deux semaines deviennent prêtes ; leur lien PDF répond 200. */
async function checkLessons(page: Page, request: APIRequestContext): Promise<void> {
  await page.goto("/apprendre/lecons");
  await expect(async () => {
    await page.reload();
    await expect(page.getByText("Prête", { exact: true })).toHaveCount(2, { timeout: 2_000 });
  }).toPass({ timeout: 120_000 });
  const links = page.getByRole("link", { name: /^Lire « / });
  const hrefs = await links.evaluateAll((all) => all.map((a) => a.getAttribute("href") ?? ""));
  expect(hrefs).toHaveLength(2);
  for (const href of hrefs) {
    await page.goto(href);
    // La leçon est « prête » avant que son PDF soit rendu : le lien paraît au rechargement.
    const pdf = page.getByRole("link", { name: "Télécharger le PDF" });
    await expect(async () => {
      await page.reload();
      await expect(pdf).toBeVisible({ timeout: 2_000 });
    }).toPass({ timeout: 60_000 });
    const response = await request.get((await pdf.getAttribute("href")) ?? "");
    expect(response.status()).toBe(200);
    expect((await response.body()).subarray(0, 4).toString()).toBe("%PDF");
  }
}

test("un objectif mène à un programme validé avec ses leçons", async ({ page, request }) => {
  await openCouncil(page);
  await expect(page.getByText(/Ouvre l'onglet Propositions pour choisir/)).toBeVisible({
    timeout: 90_000,
  });
  await checkDebate(page);
  await checkBoardAndChoose(page);

  await moveTaskWithKeyboard(page);
  await checkWeeklyLoad(page);
  await page.getByRole("button", { name: "Valider le programme" }).click();
  await expect(page.getByText("Programme validé", { exact: true })).toBeVisible({
    timeout: 30_000,
  });

  await checkLessons(page, request);
});
