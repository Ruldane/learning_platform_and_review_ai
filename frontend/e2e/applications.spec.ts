import { expect, test, type Locator, type Page } from "@playwright/test";
import { POSTING_TEXT } from "./support/samplePosting.ts";
import { finishFirstLaunch } from "./support/firstLaunch.ts";

/**
 * Parcours de bout en bout n° 3, « une candidature suit son cycle, du doublon à la relance »
 * (SPEC 18.2), contre le serveur de bout en bout (`tests.e2e.server`) : le seul modèle scripté est
 * l'Assistant de suivi (`applications_script.py`, une lecture de phrase) et l'Analyste du CV lit les
 * offres ; la page du lien de l'offre est factice, tout le reste est l'application réelle.
 *
 * Aucune horloge truquée : la date de candidature (8 jours avant aujourd'hui) fait le délai de la
 * relance de 7 jours, due depuis la veille ; « hier » de la phrase est lu par le script dans le
 * prompt du serveur. Il se joue seul ou avec les parcours n° 1 et n° 2 (même serveur, même base) :
 * les offres du n° 3 (collée, et page du lien) portent chacune une ligne de
 * référence qui les distingue de celle du n° 2 (une offre de même empreinte de texte serait rendue
 * telle quelle, sans offre nouvelle).
 *
 * L'Analyste scripté lit les offres du n° 3 sous un autre intitulé que celle du n° 2 (même
 * entreprise) : leurs fiches ne se prennent pas l'une pour l'autre, quel que soit l'ordre. La fiche
 * « Société Fictive / Développeuse IA (H/F) » est faite à la main : seule elle ressemble à la phrase
 * (même entreprise, titre proche : alerte « probable »).
 */
const COMPANY = "Société Fictive";
const POSTING_TITLE = "Ingénieure IA appliquée"; // lu par l'Analyste scripté du n° 3
const MANUAL_TITLE = "Développeuse IA (H/F)";
const SENTENCE = "j'ai postulé hier chez Société Fictive pour le poste Développeuse IA";
const POSTING_URL = "https://societe-fictive.example.org/offres/ai-product-engineer";
const PASTED_POSTING = `${POSTING_TEXT}\nRéférence interne : parcours n° 3 (texte collé).\n`;
const APPLIED_DAYS_AGO = 8;

/** `AAAA-MM-JJ` du jour local, `back` jours avant aujourd'hui. */
function isoDay(back: number): string {
  const day = new Date();
  day.setDate(day.getDate() - back);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}`;
}

/** « 7 novembre » comme le serveur l'écrit (« 1er », l'année ajoutée si ce n'est pas la courante). */
function dayText(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number) as [number, number, number];
  const months = new Intl.DateTimeFormat("fr-FR", { month: "long" });
  const name = months.format(new Date(year, month - 1, day));
  const withYear = year === new Date().getFullYear() ? "" : ` ${year}`;
  return `${day === 1 ? "1er" : day} ${name}${withYear}`;
}

const appliedOn = isoDay(APPLIED_DAYS_AGO);

/** L'offre analysée : la page rend sa candidature (le bloc « Candidature pour cette offre »). */
function candidacy(page: Page): Locator {
  return page.getByRole("region", { name: "Candidature pour cette offre" });
}

/** 1. Offre collée en texte, analysée ; fiche créée depuis la page de l'offre. */
async function createFromPosting(page: Page): Promise<void> {
  await page.goto("/carriere/offres");
  await page.getByRole("tab", { name: "Texte" }).click();
  await page.getByRole("textbox", { name: "Texte de l'offre" }).fill(PASTED_POSTING);
  await page.getByRole("button", { name: "Analyser l'offre" }).click();
  await expect(page).toHaveURL(/\/carriere\/offres\/[^/]+$/);

  // Après le parcours n° 2, la fiche de son offre (même entreprise, texte voisin) est un doublon
  // « possible » : le serveur l'alerte, et January confirme que c'est un autre poste.
  const create = candidacy(page).getByRole("button", { name: "Créer la candidature" });
  const distinct = candidacy(page).getByRole("button", { name: "C'est un autre poste" });
  await expect(create.or(distinct)).toBeVisible({ timeout: 90_000 });
  await ((await distinct.count()) > 0 ? distinct : create).click();
  await expect(page).toHaveURL(/\/candidatures\/[^/]+$/);
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByLabel("Entreprise")).toHaveValue(COMPANY);
  await expect(drawer.getByLabel("Poste")).toHaveValue(POSTING_TITLE);
}

/** 2. « J'ai postulé » à une date 8 jours avant aujourd'hui : la fiche passe en Postulée. */
async function markApplied(page: Page): Promise<void> {
  const drawer = page.getByRole("dialog");
  await drawer.getByLabel("Date de candidature").fill(appliedOn);
  await drawer.getByRole("button", { name: "J'ai postulé" }).click();
  await expect(page.getByText("Statut changé : Postulée.")).toBeVisible();
  await expect(drawer.getByLabel("Postulée le")).toHaveValue(appliedOn);
  await drawer.getByRole("button", { name: "Fermer la fiche" }).click();
  await expect(drawer).toBeHidden();
}

/** 3. La même offre, par son lien : sa page porte l'alerte « tu as déjà postulé … ». */
async function pasteSameLink(page: Page): Promise<void> {
  await page.goto("/carriere/offres");
  await page.getByRole("tab", { name: "Lien" }).click();
  await page.getByRole("textbox", { name: "Lien de l'offre" }).fill(POSTING_URL);
  await page.getByRole("button", { name: "Analyser l'offre" }).click();
  await expect(page).toHaveURL(/\/carriere\/offres\/[^/]+$/);

  const alert = candidacy(page).getByRole("alert");
  await expect(alert).toBeVisible({ timeout: 90_000 });
  await expect(alert).toContainText(
    `Attention, tu as déjà postulé chez ${COMPANY} pour le poste ${POSTING_TITLE} le ${dayText(appliedOn)}`,
  );
  await expect(alert).toContainText("Postulée");
  // Une alerte bloque : « Créer la candidature » ne se propose plus, les trois choix restent.
  await expect(candidacy(page).getByRole("button", { name: "Créer la candidature" })).toHaveCount(
    0,
  );
  await expect(alert.getByRole("button", { name: "Ouvrir la fiche existante" })).toBeVisible();
}

/** 4. La fiche faite à la main, que la phrase de l'étape suivante rappellera. */
async function createManualApplication(page: Page): Promise<void> {
  await page.goto("/candidatures/nouvelle");
  const manual = page.getByRole("region", { name: "À la main" });
  await manual.getByLabel("Entreprise").fill(COMPANY);
  await manual.getByLabel("Poste").fill(MANUAL_TITLE);
  await manual.getByRole("button", { name: "Créer la fiche" }).click();
  await expect(page).toHaveURL(/\/candidatures\/[^/]+$/);
  const drawer = page.getByRole("dialog");
  await expect(drawer.getByLabel("Poste")).toHaveValue(MANUAL_TITLE);
  await drawer.getByRole("button", { name: "Fermer la fiche" }).click();
  await expect(drawer).toBeHidden();
}

/** 5. La phrase : la carte de confirmation montre l'alerte ; « Annuler » ne crée rien. */
async function sayItAndCancel(page: Page): Promise<void> {
  await page.goto("/candidatures/nouvelle");
  await page.getByRole("textbox", { name: "Ta phrase" }).fill(SENTENCE);
  await page.getByRole("button", { name: "Préparer la fiche" }).click();

  const card = page.getByRole("region", { name: /^Je crée cette fiche \?/ });
  await expect(card).toBeVisible({ timeout: 90_000 });
  await expect(card).toContainText(
    `Attention, tu as déjà une fiche chez ${COMPANY} pour le poste ${MANUAL_TITLE}`,
  );
  await expect(card.getByLabel("Entreprise")).toHaveValue(COMPANY);
  await expect(card.getByLabel("Poste")).toHaveValue("Développeuse IA");
  await expect(card.getByLabel("Date de candidature")).toHaveValue(isoDay(1)); // « hier », lu par le script
  // Avec une alerte, le serveur ne propose pas « Créer la fiche » : « autre poste », ouvrir, annuler.
  await expect(card.getByRole("button", { name: "Créer la fiche" })).toHaveCount(0);
  await expect(card.getByRole("button", { name: "C'est un autre poste" })).toBeVisible();
  await expect(card.getByRole("button", { name: "Ouvrir la fiche existante" })).toBeVisible();

  await card.getByRole("button", { name: "Annuler" }).click();
  await expect(page.getByText("Rien n'a été créé.")).toBeVisible({ timeout: 30_000 });

  await page.goto("/candidatures");
  const todo = page.getByRole("group", { name: /^À postuler, / });
  await expect(todo.getByText(MANUAL_TITLE)).toBeVisible();
  await expect(page.getByText("Développeuse IA", { exact: true })).toHaveCount(0);
}

/** 6. La pastille de la navigation, puis la page Relances : la relance de 7 jours et son brouillon. */
async function reminderIsDue(page: Page): Promise<Locator> {
  const menu = page.getByRole("navigation", { name: "Navigation principale" });
  await menu.getByRole("link", { name: "Carrière, 1 relance due" }).click();
  await page.getByRole("link", { name: "Ouvrir Relances", exact: true }).click();
  await expect(page).toHaveURL(/\/candidatures\/relances$/);

  const list = page.getByRole("list", { name: "Relances à traiter" });
  const reminder = list.getByRole("listitem").first();
  await expect(list.getByRole("listitem")).toHaveCount(1);
  await expect(reminder).toContainText("Relance LinkedIn à 7 jours");
  await expect(reminder).toContainText(`${COMPANY}, poste ${POSTING_TITLE}`);
  await expect(reminder).toContainText(`J'ai postulé le ${dayText(appliedOn)}`); // le brouillon
  return reminder;
}

/** 7. « Copier » (le brouillon est dans le presse-papiers), puis « Fait » : la fiche est relancée. */
async function copyAndDone(page: Page, reminder: Locator): Promise<void> {
  await reminder.getByRole("button", { name: "Copier" }).click();
  await expect(page.getByText("Brouillon copié.")).toBeVisible();
  const copied = await page.evaluate<string>("navigator.clipboard.readText()");
  expect(copied).toContain(`au poste de ${POSTING_TITLE} chez ${COMPANY}`);

  await reminder.getByRole("button", { name: "Fait" }).click();
  await expect(page.getByText("Relance traitée.")).toBeVisible();
  await expect(page.getByRole("list", { name: "Relances à traiter" })).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Navigation principale" })
    .getByRole("link", { name: /^Carrière/ })).toHaveAccessibleName("Carrière");
}

/** 8. La fiche passe Relancée, et son fil montre la relance. */
async function followedUp(page: Page): Promise<void> {
  await page.goto("/candidatures");
  const column = page.getByRole("group", { name: /^Relancée, 1/ });
  const open = column.getByRole("button", { name: new RegExp(`^Ouvrir la fiche de ${COMPANY}`) });
  await expect(open).toBeVisible();
  await open.click();

  const drawer = page.getByRole("dialog");
  const timeline = drawer.getByRole("list", { name: "Historique de la candidature" });
  await expect(timeline).toContainText("Relance faite : message LinkedIn.");
  await expect(timeline).toContainText("Postulée → Relancée");
  // Celle de 7 jours est faite : restent les suivantes, pas encore dues.
  const pending = drawer.getByRole("region", { name: "Relances de cette fiche" });
  await expect(
    pending.getByRole("heading", { name: "Relance par e-mail à 14 jours" }),
  ).toBeVisible();
  await expect(pending.getByRole("heading", { name: "Relance LinkedIn à 7 jours" })).toHaveCount(0);
  await drawer.getByRole("button", { name: "Fermer la fiche" }).click();
  await expect(drawer).toBeHidden();
}

/** La poignée de la carte de la fiche relancée (et la colonne qui la porte). */
function handle(page: Page): Locator {
  return page.getByRole("button", { name: `Glisser « ${POSTING_TITLE} » (${COMPANY})` });
}

/**
 * Poignée au focus, espace : la carte est saisie, au-dessus de sa colonne `from` (dnd-kit
 * n'écoute les flèches qu'une fois saisie : on attend son annonce, comme le ferait un lecteur).
 */
async function grab(page: Page, announcer: Locator, from: string): Promise<void> {
  await handle(page).focus();
  await page.keyboard.press("Space");
  await expect(announcer).toContainText(`« ${POSTING_TITLE} » est au-dessus de la colonne ${from}`);
}

/**
 * 9. Le glisser-déposer au clavier de dnd-kit, jamais joué dans un vrai navigateur : poignée,
 * espace, flèche droite, espace. La carte tombe dans la colonne voisine, le déplacement est
 * annoncé et enregistré ; puis le même geste en sens inverse la ramène en « Relancée ».
 */
async function keyboardDrag(page: Page): Promise<void> {
  await page.goto("/candidatures");
  const announcer = page.locator('[id^="DndLiveRegion"]');
  const followedUpColumn = page.getByRole("group", { name: /^Relancée, / });
  const interviewColumn = page.getByRole("group", { name: /^Entretien, / });
  await expect(followedUpColumn.getByRole("listitem")).toHaveCount(1);

  await grab(page, announcer, "Relancée");
  await page.keyboard.press("ArrowRight");
  await expect(announcer).toContainText(
    `« ${POSTING_TITLE} » est au-dessus de la colonne Entretien`,
  );
  await page.keyboard.press("Space");
  await expect(announcer).toContainText(`« ${POSTING_TITLE} » déposée dans la colonne Entretien`);
  await expect(interviewColumn.getByRole("listitem")).toHaveCount(1);
  await expect(followedUpColumn.getByRole("listitem")).toHaveCount(0);
  await expect(handle(page)).toBeFocused(); // le focus suit la carte (poignée)

  // L'écriture a eu lieu : la page relue montre la carte dans sa nouvelle colonne.
  await page.reload();
  await expect(interviewColumn.getByRole("listitem")).toHaveCount(1);

  await grab(page, announcer, "Entretien");
  await page.keyboard.press("ArrowLeft");
  await expect(announcer).toContainText(
    `« ${POSTING_TITLE} » est au-dessus de la colonne Relancée`,
  );
  await page.keyboard.press("Space");
  await expect(announcer).toContainText(`« ${POSTING_TITLE} » déposée dans la colonne Relancée`);
  await expect(followedUpColumn.getByRole("listitem")).toHaveCount(1);
  await expect(interviewColumn.getByRole("listitem")).toHaveCount(0);
}

// Le premier lancement est fait avant la première page (la porte mène sinon à /bienvenue).
test.beforeEach(({ request }) => finishFirstLaunch(request));

test("une candidature suit son cycle, du doublon à la relance", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);

  await test.step("offre collée, fiche créée depuis sa page", () => createFromPosting(page));
  await test.step("« J'ai postulé » il y a 8 jours", () => markApplied(page));
  await test.step("la même offre par son lien : alerte « déjà postulé »", () =>
    pasteSameLink(page));
  await test.step("la fiche « Développeuse IA (H/F) » faite à la main", () =>
    createManualApplication(page));
  await test.step("la phrase : carte de confirmation avec l'alerte, « Annuler »", () =>
    sayItAndCancel(page));
  const reminder = await test.step("la relance de 7 jours, son brouillon, la pastille", () =>
    reminderIsDue(page));
  await test.step("« Copier » puis « Fait »", () => copyAndDone(page, reminder));
  await test.step("la fiche est Relancée, son fil montre la relance", () => followedUp(page));
  await test.step("glisser-déposer au clavier, aller et retour", () => keyboardDrag(page));
});
