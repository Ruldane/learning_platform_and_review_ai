import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

/**
 * Parcours de bout en bout n° 4, « le brief du jour à l'ouverture et un relevé du radar » (SPEC
 * 18.2, F17, P18), contre le serveur de bout en bout (`tests.e2e.server`) : les agents sont
 * scriptés (`daily_script.py` : l'Éclaireur choisit la ressource, le Modérateur écrit le conseil,
 * l'Analyste lit les offres), le web est factice (trois ressources, huit offres lisibles et trois
 * pages bloquées) ; tout le reste est l'application réelle. Le planificateur du serveur est coupé :
 * le brief que l'on voit est donc bien celui de l'ouverture (`GET /brief/today`).
 *
 * Le sujet de la ressource vient du poste des réglages du radar : le parcours le pose avant d'ouvrir
 * l'accueil (sans poste, objectif ni programme, le brief n'a aucune ressource à chercher). Il se joue
 * seul ou après les parcours n° 1 à n° 3 (même serveur, même base) : aucune de ses vérifications ne
 * suppose l'accueil vide, et l'accueil n'est ouvert par aucun autre parcours avant lui.
 */
const API = `${process.env.E2E_API_URL ?? "http://localhost:8765"}/api/v1`;
const ROLE = "Ingénieure données";
const ZONE = "Lyon";
const RESOURCE_TITLE = "Construire une plateforme de données fiable";
const RESOURCE_URL = "https://ingenierie-donnees.example.org/plateforme-fiable";
const RESOURCE_WHY = "Un état des lieux récent du métier, utile pour ton poste visé.";
const ADVICE = [
  "Commence par ton bloc d'étude du jour, puis garde un moment pour les révisions.",
  "Les relances et les nouvelles offres peuvent attendre la fin de ta session.",
];

/** Le poste visé des réglages du radar : c'est lui qui donne son sujet à la ressource du brief. */
async function setRadarRole(request: APIRequestContext): Promise<void> {
  const current = await request.get(`${API}/settings`);
  expect(current.ok()).toBe(true);
  const settings = { ...(await current.json()), radar_role: ROLE, radar_zone: ZONE };
  expect((await request.put(`${API}/settings`, { data: settings })).ok()).toBe(true);
}

/** Les sessions du brief du jour : une seule, quel que soit le nombre d'ouvertures. */
async function briefSessions(request: APIRequestContext): Promise<number> {
  const response = await request.get(`${API}/sessions?graph=daily_brief`);
  expect(response.ok()).toBe(true);
  return ((await response.json()) as unknown[]).length;
}

/**
 * Les sept rubriques de F17. Sans programme validé (serveur neuf), le bloc et l'avancement
 * laissent la place à « Pas encore de programme » : c'est leur état vide.
 */
async function expectSevenRubrics(page: Page): Promise<void> {
  const heading = (name: string) => page.getByRole("heading", { name, exact: true });
  const noProgram = page.getByText("Pas encore de programme", { exact: true });
  await expect(heading("Ton bloc du jour").or(noProgram)).toBeVisible();
  await expect(heading("Révisions")).toBeVisible();
  await expect(heading("Relances")).toBeVisible();
  await expect(heading("Nouvelles offres")).toBeVisible();
  await expect(heading("Ta semaine").or(noProgram)).toBeVisible();
  await expect(heading("Une ressource pour toi")).toBeVisible();
  await expect(heading("Le conseil")).toBeVisible();
}

/** La ressource du jour : le lien de la page lue, son site, la raison du choix. */
async function expectResource(page: Page): Promise<void> {
  const link = page.getByRole("link", { name: RESOURCE_TITLE });
  await expect(link).toBeVisible({ timeout: 60_000 });
  await expect(link).toHaveAttribute("href", RESOURCE_URL);
  await expect(page.getByText("ingenierie-donnees.example.org, 4 novembre 2026")).toBeVisible();
  await expect(page.getByText(`Pourquoi : ${RESOURCE_WHY}`)).toBeVisible();
}

async function expectAdvice(page: Page): Promise<void> {
  for (const sentence of ADVICE) {
    await expect(page.getByText(sentence, { exact: true })).toBeVisible({ timeout: 60_000 });
  }
  await expect(page.getByText("Le conseil se réunit…")).toHaveCount(0);
}

test("le brief du jour existe à l'ouverture, sept rubriques et un seul conseil", async ({
  page,
  request,
}) => {
  await setRadarRole(request);

  await page.goto("/");
  await expectSevenRubrics(page);
  // Le brief est rendu tout de suite : le conseil, lui, se réunit (l'Éclaireur puis le Modérateur).
  await expect(page.getByText("Le conseil se réunit…")).toBeVisible();
  await expectAdvice(page);
  await expectResource(page);
  expect(await briefSessions(request)).toBe(1);

  // Recharger rend le même brief, déjà complet, sans lancer une seconde session.
  await page.reload();
  await expectSevenRubrics(page);
  await expectAdvice(page);
  await expectResource(page);
  expect(await briefSessions(request)).toBe(1);

  // Les actions rapides mènent où elles disent.
  const quick = page.getByRole("group", { name: "Actions rapides" });
  await quick.getByRole("button", { name: "Capturer" }).click();
  await expect(page.getByRole("dialog").getByText("Capture rapide")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await quick.getByRole("button", { name: "Réviser" }).click();
  await expect(page).toHaveURL(/\/etudier\/revisions$/);
});

test("un relevé du radar lit huit offres, en compte trois bloquées et paraît à l'accueil", async ({
  page,
}) => {
  await page.goto("/carriere/radar");
  await page.getByLabel("Poste visé").fill(ROLE);
  await page.getByLabel("Zone", { exact: true }).fill(ZONE);
  await page.getByRole("button", { name: "Lancer un relevé" }).click();

  // Les nombres sont ceux de la lecture réelle : huit offres lisibles, trois pages bloquées.
  await expect(page.getByText("8 offres lues · 3 bloquées · 8 analysées")).toBeVisible({
    timeout: 120_000,
  });
  await expect(page.getByText("Poste : Ingénieure données, zone : Lyon")).toBeVisible();
  await expect(page.getByRole("note")).toContainText("Échantillon réduit");
  await expect(page.getByText("Domaines bloqués (2)")).toBeVisible();

  // Premier relevé : aucune évolution à montrer, et le classement le dit.
  const ranking = page.getByRole("list", { name: "Classement des compétences" });
  await expect(ranking).toContainText("Python");
  await expect(ranking.getByText("premier relevé").first()).toBeVisible();

  // Le fil d'activité de l'accueil garde la trace du relevé, avec ses nombres réels.
  await page.goto("/");
  await expect(page.getByText("Relevé du radar : 8 offres lues, 3 bloquées")).toBeVisible();
});
