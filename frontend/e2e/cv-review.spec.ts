import { expect, test, type APIRequestContext, type Locator, type Page } from "@playwright/test";
import { SAMPLE_CV_SHA256, sampleCvPdf, sampleCvSha256 } from "./support/sampleCv.ts";
import { POSTING_TEXT } from "./support/samplePosting.ts";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

/**
 * Parcours de bout en bout n° 2, « revue complète d'un CV » (SPEC 18.2), contre le serveur de bout
 * en bout (`tests.e2e.server`) : les réponses des agents (Archiviste, Maquettiste, Analyste,
 * Éclaireur, Lecteur ATS, Recruteur) sont scriptées (`cv_script.py`), le rendu du PDF est textuel
 * (`TextHtmlRenderer`), tout le reste est l'application réelle. Il se joue seul ou après le parcours
 * n° 1 (`merge_scripts` : l'Éclaireur du Conseil et celui de la fiche entreprise ont chacun leur file).
 *
 * Ce que le script fait dire : trois modifications à décider (deux sans fait nouveau, une avec un
 * chiffre absent du profil, donc « à confirmer ») et un mot clé de l'offre (RAG) absent du profil,
 * parti vers l'écart au lieu d'entrer dans le CV.
 */
const FILENAME = "CV_Camille_Exemple_Societe_Fictive_AI_Product_Engineer.pdf";
const ACCEPTED_LINE = "Conçu et mis en production"; // a1, acceptée en groupe
const CONFIRMED_LINE = "Réduit de 40"; // a2, « à confirmer » puis confirmée
const GAP_LINE = "chaîne RAG"; // a3, partie vers l'écart : jamais dans le PDF

function pdfFile() {
  return { name: "cv-camille-exemple.pdf", mimeType: "application/pdf", buffer: sampleCvPdf() };
}

/** 1. Profil : dépôt du PDF, brouillon relu, profil validé. */
async function createProfile(page: Page): Promise<void> {
  await page.goto("/career/profile");
  await page.getByLabel("Ton CV (PDF)", { exact: true }).setInputFiles(pdfFile());
  await page.getByRole("button", { name: "Créer mon profil maître" }).click();
  const validate = page.getByRole("button", { name: "Valider mon profil" });
  await expect(validate).toBeVisible({ timeout: 90_000 });
  await validate.click();
  const saved = page.getByRole("status").filter({ hasText: /Profil validé : version \d+\./ });
  await expect(saved).toBeVisible();
}

/** 2. Modèles : le même PDF, les passes du Maquettiste, puis « Valider ». */
async function createTemplate(page: Page): Promise<void> {
  await page.goto("/career/cv");
  await page.getByLabel("Ton CV (PDF, 4 pages au plus)").setInputFiles(pdfFile());
  await page.getByRole("button", { name: "Créer le modèle" }).click();
  await expect(page).toHaveURL(/\/career\/cv\/templates\/[^/]+$/);

  const validate = page.getByRole("button", { name: "Valider", exact: true });
  await expect(validate).toBeVisible({ timeout: 120_000 });
  const feed = page.getByRole("region", { name: "Fil du Maquettiste" });
  await expect(feed.getByText(/Passe 1 : le rendu ressemble à ton CV à \d+ %/)).toBeVisible();
  await expect(page.getByText(/Ressemblance : \d+ %/).first()).toBeVisible();
  await validate.click();
  await expect(page.getByText("Ce modèle est prêt.")).toBeVisible({ timeout: 30_000 });
}

/** 3. Offres : le texte de l'offre collé, son score de match et son tableau d'écarts. */
async function addPosting(page: Page): Promise<void> {
  await page.goto("/career/postings");
  await page.getByRole("tab", { name: "Texte" }).click();
  await page.getByRole("textbox", { name: "Texte de l'offre" }).fill(POSTING_TEXT);
  await page.getByRole("button", { name: "Analyser l'offre" }).click();
  await expect(page).toHaveURL(/\/career\/postings\/[^/]+$/);

  await expect(page.getByRole("meter", { name: /^Score de match : \d+ sur 100$/ })).toBeVisible({
    timeout: 90_000,
  });
  const gap = page.getByRole("table", { name: "Écart avec l'offre" });
  await expect(gap).toBeVisible();
  for (const skill of ["Python", "LangGraph", "RAG"]) {
    await expect(gap.getByRole("row", { name: new RegExp(skill) }).first()).toBeVisible();
  }
}

/** Les cartes des modifications (le fil de la revue a aussi des articles : « Pourquoi » les isole). */
function cards(page: Page): Locator {
  return page.getByRole("article").filter({ hasText: "Pourquoi" });
}

/** 4. La revue : le fil des agents, puis les trois modifications proposées. */
async function startReview(page: Page): Promise<void> {
  await page.getByRole("link", { name: "Revoir mon CV pour cette offre" }).click();
  await expect(page).toHaveURL(/\/career\/cv\/reviews\/[^/]+$/);
  await expect(cards(page)).toHaveCount(3, { timeout: 180_000 });
  const feed = page.getByRole("region", { name: "Fil de la revue" });
  await expect(feed.getByText("Lecteur ATS", { exact: true }).first()).toBeVisible();
  await expect(feed.getByText("Recruteur", { exact: true }).first()).toBeVisible();
  // Le mot clé de l'offre absent du profil part vers l'écart : il n'est pas une modification.
  await expect(page.getByText(/1 mot clé de l'offre part vers l'écart/).first()).toBeVisible();
}

/** 5. « Tout accepter » laisse la modification « à confirmer » ; la case cochée l'accepte. */
async function decide(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Tout accepter" }).click();
  await expect(page.getByText("Acceptée", { exact: true })).toHaveCount(2);
  await expect(
    page.getByText("Modifications acceptées. 1 modification à confirmer une par une."),
  ).toBeVisible();

  const toConfirm = cards(page).filter({ hasText: "À confirmer" });
  await expect(toConfirm).toHaveCount(1);
  await toConfirm.getByRole("checkbox", { name: "Je confirme que c'est vrai" }).check();
  await toConfirm.getByRole("button", { name: "Accepter" }).click();
  await expect(page.getByText("Acceptée", { exact: true })).toHaveCount(3);
  await expect(page.getByText("Toutes les modifications sont acceptées.")).toBeVisible();
}

/** 6 et 7. « Générer le PDF », aperçu d'une page, puis le fichier téléchargé. */
async function generate(page: Page, request: APIRequestContext): Promise<void> {
  await page.getByRole("button", { name: "Générer le PDF" }).click();
  await expect(page.getByText("1 page, comme ton CV d'origine")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByRole("img", { name: "Page 1 sur 1 du CV" })).toBeVisible();

  const link = page.getByRole("link", { name: `Télécharger ${FILENAME}` });
  await expect(link).toBeVisible();
  const response = await request.get((await link.getAttribute("href")) ?? "");
  expect(response.status()).toBe(200);
  expect(response.headers()["content-disposition"]).toContain(FILENAME);
  const body = await response.body();
  expect(body.subarray(0, 4).toString()).toBe("%PDF");
  const text = body.toString("latin1"); // le flux de `make_pdf` : une ligne par `Tj`, en cp1252
  expect(text).toContain("Camille Exemple");
  expect(text).toContain(ACCEPTED_LINE);
  expect(text).toContain(CONFIRMED_LINE);
  expect(text).not.toContain(GAP_LINE);
}

/** 8. « Terminer » : la revue est close, la version reste dans « Versions ». */
async function finish(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Terminer" }).click();
  await expect(
    page.getByText("Revue terminée : tes décisions et tes versions restent ici."),
  ).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("La revue est terminée : les décisions sont figées.")).toBeVisible();

  await page.goto("/career/cv/versions");
  const group = page.getByRole("region", { name: /^Versions pour l'offre AI Product Engineer/ });
  await expect(group.getByText("Version 1").first()).toBeVisible();
  await expect(group.getByText("Prête").first()).toBeVisible();
}

// Le premier lancement est fait avant la première page (la porte mène sinon à /welcome).
test.beforeEach(({ request }) => finishFirstLaunch(request));

test("un CV est revu face à une offre jusqu'à son PDF", async ({ page, request }) => {
  expect(sampleCvSha256()).toBe(SAMPLE_CV_SHA256); // le même CV fictif que celui de Python
  await createProfile(page);
  await createTemplate(page);
  await addPosting(page);
  await startReview(page);
  await decide(page);
  await generate(page, request);
  await finish(page);
});
