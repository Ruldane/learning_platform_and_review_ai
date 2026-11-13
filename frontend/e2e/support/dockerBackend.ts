import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

/**
 * `pnpm e2e:docker [arguments de playwright]` : les parcours contre un back lancé dans l'image du
 * back (poste où Python ne tourne que dans Docker, D97 n° 16), dépôt monté sur `/repo`, base neuve.
 *
 * Arrêt (D117) : `--init` donne au conteneur un vrai PID 1 qui relaie les signaux ; sous Linux et
 * macOS, `exec` fait du client `docker` le processus que Playwright arrête par `SIGTERM`
 * (`gracefulShutdown`), relayé jusqu'au serveur. Windows ignore `gracefulShutdown` et n'a pas
 * `exec` : le démontage global (`teardown.ts`) retire le conteneur par son nom
 * (`E2E_DOCKER_NAME`), et le client `docker` se termine avec lui.
 */
const NAME = "tremplin-e2e-backend";
const repo = resolve(import.meta.dirname, "../../..").replaceAll("\\", "/");

const run = [
  `docker run --rm --init --name ${NAME} -p 8765:8765`,
  `-v "${repo}:/repo" -v tremplin-devvenv:/opt/venv -v tremplin-uvcache:/root/.cache/uv`,
  "-w /repo/backend --user root -e UV_PROJECT_ENVIRONMENT=/opt/venv -e UV_LINK_MODE=copy",
  "-e PYTHONDONTWRITEBYTECODE=1 --entrypoint uv learning_career_platform-backend:latest",
  "run python -m tests.e2e.server --port 8765 --host 0.0.0.0",
  `--data-dir /tmp/e2e-${Date.now()} --origin http://localhost:5180`,
].join(" ");
const command = process.platform === "win32" ? run : `exec ${run}`;

spawnSync("docker", ["rm", "-f", NAME], { stdio: "ignore" }); // reste d'un passage interrompu
const result = spawnSync("pnpm", ["exec", "playwright", "test", ...process.argv.slice(2)], {
  stdio: "inherit",
  shell: true,
  env: { ...process.env, E2E_DOCKER_NAME: NAME, E2E_BACKEND_COMMAND: command },
});
process.exit(result.status ?? 1);
