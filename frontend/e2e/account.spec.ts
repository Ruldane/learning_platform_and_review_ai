import { readFile } from "node:fs/promises";
import { expect, test, type Page } from "@playwright/test";
import { CAMILLE, DOMINIQUE, LOCAL_NOTE } from "./support/accounts.ts";

/**
 * Parcours de bout en bout n° 5, « connexion, reprise, premier lancement, isolation et données »
 * (phase 9, SPEC 17), contre le serveur de bout en bout en **mode Google** (`playwright.auth.config.ts`) :
 * le faux fournisseur `scripts/fake_oidc.py` fait la connexion (aucun identifiant Google, aucun
 * mot de passe : `login_hint` choisit le compte). Le serveur part d'une base neuve dont l'espace
 * `local` est amorcé (`--seed-local` : une note au journal, comme un poste qui a tourné en mode
 * local) et dont `ALLOWED_EMAILS` nomme Camille et Dominique : la reprise n'est proposée qu'à une
 * adresse d'une liste explicite.
 *
 * Camille se connecte la première : elle reprend l'espace local, fait le premier lancement en
 * cinq étapes et écrit son style. Dominique, second compte, ne voit jamais la reprise, repart d'un
 * espace vide, exporte puis supprime tout : Camille retrouve ses données intactes. Les deux
 * tests partagent le même serveur et se jouent dans l'ordre.
 */
const API_URL = process.env.E2E_AUTH_API_URL ?? "http://localhost:8766";
const API = `${API_URL}/api/v1`;
const STYLE = "Phrases courtes, ton direct, pas de jargon inutile.";
const STEP_TITLES = [
  "Les services de Tremplin",
  "Ce qui sort de ta machine",
  "Ta clé d'API",
  "Ton CV",
  "Ton temps disponible",
];

test.describe.configure({ mode: "serial" });

/** L'adresse qui commence une connexion ; sans `hint`, le faux fournisseur connecte Camille. */
function loginUrl(email?: string): string {
  return `${API}/auth/google/login${email ? `?login_hint=${encodeURIComponent(email)}` : ""}`;
}

/** Quitte l'application par le menu du compte : la porte mène à `/login`. */
async function logOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Se déconnecter" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("link", { name: "Se connecter avec Google" })).toBeVisible();
}

/** Les cinq étapes du premier lancement, une à une, jusqu'à « Terminer » (CV passé). */
async function walkThroughWelcome(page: Page): Promise<void> {
  // « Suivant », « Plus tard » (sans clé), « Passer » (sans import) puis « Terminer » : jamais
  // « Passer l'accueil » (le nom doit être exactement l'un des quatre).
  const advance = page.getByRole("button", { name: /^(Suivant|Plus tard|Passer|Terminer)$/ });
  for (const [index, title] of STEP_TITLES.entries()) {
    await expect(page.getByText(`Étape ${index + 1} sur 5`)).toBeVisible();
    await expect(page.getByRole("heading", { level: 1, name: title })).toBeVisible();
    await advance.click();
  }
  await expect(page).toHaveURL(/localhost:\d+\/$/);
}

/** Réglages > Style : un texte enregistré, annoncé. */
async function saveStyle(page: Page): Promise<void> {
  await page.goto("/settings/style");
  const field = page.getByLabel("Guide de style personnel");
  await expect(field).toHaveValue("");
  await field.fill(STYLE);
  await page.getByRole("button", { name: "Enregistrer" }).click();
  await expect(page.getByText("Guide de style enregistré.")).toBeVisible();
}

/** Camille retrouve ses données : la note de l'espace local et son style. */
async function expectCamilleData(page: Page): Promise<void> {
  await page.goto("/study/journal");
  await expect(page.getByText(LOCAL_NOTE)).toBeVisible();
  await page.goto("/settings/style");
  await expect(page.getByLabel("Guide de style personnel")).toHaveValue(STYLE);
}

/** Le compte connecté, lu par l'API : le cookie de session fait foi. */
async function signedInAs(page: Page): Promise<string | null> {
  const me = await page.request.get(`${API}/auth/me`);
  return me.ok() ? ((await me.json()) as { email: string }).email : null;
}

/** Mes données : l'archive s'ouvre dans un nouvel onglet, c'est un zip qui n'est pas vide. */
async function exportData(page: Page): Promise<void> {
  const link = page.getByRole("link", { name: "Exporter toutes mes données" });
  await expect(link).toHaveAttribute("target", "_blank");
  await expect(link).toHaveAttribute("href", `${API}/account/export`);
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  expect(download.suggestedFilename()).toMatch(/^tremplin-export-\d{8}\.zip$/);
  const archive = await readFile(await download.path());
  expect(archive.length).toBeGreaterThan(100);
  expect(archive.subarray(0, 2).toString("latin1")).toBe("PK"); // l'en-tête d'un zip
}

/** « Tout supprimer » : le mot exact débloque le bouton. */
async function deleteEverything(page: Page): Promise<void> {
  const submit = page.getByRole("button", { name: "Tout supprimer" });
  await expect(submit).toBeDisabled();
  await page.getByLabel("Tape SUPPRIMER pour confirmer").fill("SUPPRIMER");
  await expect(submit).toBeEnabled();
  await submit.click();
}

test("Camille reprend l'espace local, Dominique repart de zéro et supprime tout", async ({
  page,
}) => {
  // (1) Sans session, l'application mène à la connexion ; le faux fournisseur connecte Camille.
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await page.getByRole("link", { name: "Se connecter avec Google" }).click();

  // La première connexion d'un compte nommé propose l'espace local ; Camille le reprend.
  await expect(page).toHaveURL(/\/login\/claim$/);
  await expect(page.getByRole("heading", { name: "Reprendre tes données ?" })).toBeVisible();
  await page.getByRole("button", { name: "Reprendre les données de cet ordinateur" }).click();

  // Le premier lancement est à faire (le compte repris n'a jamais fini l'accueil).
  await expect(page).toHaveURL(/\/welcome$/);
  await walkThroughWelcome(page);
  expect(await signedInAs(page)).toBe(CAMILLE);

  // La capture de l'espace local est au journal ; un texte de style est enregistré.
  await page.goto("/study/journal");
  await expect(page.getByText(LOCAL_NOTE)).toBeVisible();
  await saveStyle(page);

  // (3) Camille se déconnecte ; Dominique se connecte : jamais la page de reprise.
  await page.goto("/");
  await logOut(page);
  await page.goto(loginUrl(DOMINIQUE));
  await expect(page).toHaveURL(/\/welcome$/);
  await expect(page.getByRole("heading", { name: "Reprendre tes données ?" })).toHaveCount(0);
  expect(await signedInAs(page)).toBe(DOMINIQUE);

  // Son espace est vide : ni la note de Camille, ni son style.
  await page.getByRole("button", { name: "Passer l'accueil" }).click();
  await expect(page).toHaveURL(/localhost:\d+\/$/);
  await page.goto("/study/journal");
  await expect(page.getByText("Ton journal est vide")).toBeVisible();
  await expect(page.getByText(LOCAL_NOTE)).toHaveCount(0);
  await page.goto("/settings/style");
  await expect(page.getByLabel("Guide de style personnel")).toHaveValue("");

  // (4) Mes données : l'export, puis « Tout supprimer » ramène à la connexion.
  await page.goto("/settings/data");
  await exportData(page);
  await deleteEverything(page);
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("link", { name: "Se connecter avec Google" })).toBeVisible();
  expect(await signedInAs(page)).toBeNull();

  // (5) Camille se reconnecte : rien n'a bougé pour elle.
  await page.getByRole("link", { name: "Se connecter avec Google" }).click();
  await expect(page).toHaveURL(/localhost:\d+\/$/);
  expect(await signedInAs(page)).toBe(CAMILLE);
  await expectCamilleData(page);
});

// Revue finale de la phase 9 (C-I2) : avant le correctif, l'onglet A (Dominique) envoyait
// `POST /account/delete` avec le cookie de l'onglet B (Camille) et supprimait Camille (vu sur Edge).
test("« Tout supprimer » n'efface pas le compte d'un autre onglet", async ({ context, page }) => {
  const other = await context.newPage();
  // Onglet A : Dominique (un compte neuf : son premier lancement est passé) sur Mes données.
  await page.goto(loginUrl(DOMINIQUE));
  await expect(page).toHaveURL(/\/welcome$/);
  await page.getByRole("button", { name: "Passer l'accueil" }).click();
  await expect(page).toHaveURL(/localhost:\d+\/$/);
  await page.goto("/settings/data");
  await expect(page.getByRole("heading", { name: "Tout supprimer" })).toBeVisible();
  await expect(page.getByText(`Compte à effacer : ${DOMINIQUE}`)).toBeVisible();

  // Le cookie change après que le serveur a lu l'identité de Dominique et avant le POST.
  await page.route(
    `${API}/auth/me`,
    async (route) => {
      const response = await route.fetch();
      expect((await response.json()).email).toBe(DOMINIQUE);
      await other.goto(loginUrl(CAMILLE));
      await expect(other).toHaveURL(/localhost:\d+\/$/);
      await route.fulfill({ response });
    },
    { times: 1 },
  );
  const refused = page.waitForResponse((response) => response.url().endsWith("/account/delete"));
  await deleteEverything(page);
  expect((await refused).status()).toBe(409);
  await expect(page.getByTestId("delete-failure")).toContainText("Rien n'a été supprimé");
  await expect(page.getByText(`Compte à effacer : ${CAMILLE}`)).toBeVisible();
  await expect(page.getByLabel("Tape SUPPRIMER pour confirmer")).toHaveValue("");
  await expect(page.getByRole("button", { name: "Tout supprimer" })).toBeDisabled();

  // Camille est toujours connectée, et ses données sont intactes.
  expect(await signedInAs(other)).toBe(CAMILLE);
  await expectCamilleData(other);
});
