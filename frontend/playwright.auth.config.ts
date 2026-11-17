import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig, devices } from "@playwright/test";
import { ALLOWED_EMAILS } from "./e2e/support/accounts.ts";

/**
 * Parcours de bout en bout n° 5, « connexion, reprise, isolation et données » (phase 9, SPEC 17) :
 * le back de bout en bout en **mode Google** (`tests.e2e.server --auth google` : le faux fournisseur
 * `scripts/fake_oidc.py` est monté sous `/fake-oidc` du même serveur, aucun identifiant Google),
 * sur une base neuve dont l'espace `local` est amorcé (`--seed-local` : une ligne de journal à
 * reprendre) et dont `ALLOWED_EMAILS` est une liste **explicite** (la reprise de l'espace local
 * n'est jamais proposée avec `*`). Le front Vite pointe dessus. Mêmes gardes que
 * `playwright.config.ts`, sur d'autres ports (API 8766, front 5181) : les deux jeux de parcours
 * peuvent tourner l'un après l'autre sans se gêner.
 *
 * `E2E_AUTH_API_URL` remplace l'adresse de l'API (boucle locale seulement) ;
 * `E2E_BACKEND_COMMAND` remplace la commande du back (Docker : `E2E_DOCKER_AUTH=1 pnpm e2e:docker
 * -c playwright.auth.config.ts`, voir `e2e/support/dockerBackend.ts`, qui ajoute
 * `--in-container` : le port n'y est publié que sur la boucle locale de l'hôte).
 */
const API_PORT = 8766;
const WEB_PORT = 5181;
const apiUrl = process.env.E2E_AUTH_API_URL ?? `http://localhost:${API_PORT}`;
if (!["localhost", "127.0.0.1"].includes(new URL(apiUrl).hostname)) {
  throw new Error("E2E_AUTH_API_URL doit viser localhost ou 127.0.0.1 : jamais une API réelle.");
}
const webUrl = `http://localhost:${WEB_PORT}`;
const dataDir = join(tmpdir(), `tremplin-e2e-auth-${Date.now()}`);
const backendCommand =
  process.env.E2E_BACKEND_COMMAND ??
  [
    `uv run python -m tests.e2e.server --auth google --port ${API_PORT} --data-dir "${dataDir}"`,
    `--origin ${webUrl} --allowed-emails ${ALLOWED_EMAILS} --seed-local`,
  ].join(" ");

export default defineConfig({
  testDir: "./e2e",
  testMatch: "account.spec.ts",
  globalTeardown: "./e2e/support/teardown.ts",
  timeout: 240_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  // Rapports et traces hors du dépôt : ni `playwright-report/` ni `test-results/` ne sont partagés avec
  // le jeu de parcours n° 1 à n° 4.
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: join(tmpdir(), "tremplin-e2e-auth-report") }],
  ],
  outputDir: join(tmpdir(), "tremplin-e2e-auth-results"),
  use: {
    ...devices["Desktop Chrome"],
    // Chromium complet, comme `playwright.config.ts` (`chrome-headless-shell` est bloqué sous
    // Windows par le contrôle d'applications).
    channel: "chromium",
    baseURL: webUrl,
    viewport: { width: 1280, height: 900 },
    locale: "fr-FR",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: backendCommand,
      cwd: "../backend",
      url: `${apiUrl}/api/v1/health`,
      reuseExistingServer: process.env.E2E_REUSE_BACKEND === "1",
      timeout: 180_000,
      stdout: "pipe",
      gracefulShutdown: { signal: "SIGTERM", timeout: 10_000 },
    },
    {
      command: `node node_modules/vite/bin/vite.js --port ${WEB_PORT} --strictPort`,
      url: webUrl,
      env: { VITE_API_URL: apiUrl },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
