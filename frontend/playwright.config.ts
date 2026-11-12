import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig, devices } from "@playwright/test";

/**
 * Parcours de bout en bout (SPEC 18.2) : le back de bout en bout (`tests.e2e.server` : vraie
 * application, fournisseurs factices, modèles scriptés) et le front Vite qui pointe dessus.
 *
 * Le serveur du back joue son script une seule fois : il démarre sur une base neuve à chaque
 * passage, dans un dossier temporaire du système (il refuse tout dossier qui pourrait contenir des
 * données réelles). `E2E_BACKEND_COMMAND` remplace sa commande (Docker, par exemple) ; avec
 * `E2E_REUSE_BACKEND=1`, un serveur déjà lancé sur `E2E_API_URL` est repris tel quel. L'API doit
 * rester locale, et Vite est toujours relancé : un Vite déjà ouvert pourrait viser une autre API.
 */
const API_PORT = 8765;
const WEB_PORT = 5180;
const apiUrl = process.env.E2E_API_URL ?? `http://localhost:${API_PORT}`;
if (!["localhost", "127.0.0.1"].includes(new URL(apiUrl).hostname)) {
  throw new Error("E2E_API_URL doit viser localhost ou 127.0.0.1 : jamais une API réelle.");
}
const webUrl = `http://localhost:${WEB_PORT}`;
const dataDir = join(tmpdir(), `tremplin-e2e-${Date.now()}`);
const backendCommand =
  process.env.E2E_BACKEND_COMMAND ??
  `uv run python -m tests.e2e.server --port ${API_PORT} --data-dir "${dataDir}" --origin ${webUrl}`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 240_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    ...devices["Desktop Chrome"],
    // Chromium complet (nouveau mode sans tête) plutôt que `chrome-headless-shell` : ce dernier
    // est bloqué par le contrôle d'applications de Windows sur le poste de développement.
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
    },
    {
      command: `pnpm exec vite --port ${WEB_PORT} --strictPort`,
      url: webUrl,
      env: { VITE_API_URL: apiUrl },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
