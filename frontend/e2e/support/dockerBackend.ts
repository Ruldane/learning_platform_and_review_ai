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
 * (`E2E_DOCKER_NAME`), et le client `docker` se termine avec lui. Le lanceur le retire aussi à la
 * fin, quoi qu'il arrive : Playwright ne fait pas son démontage global si le back n'a pas démarré,
 * ni après un Ctrl+C.
 *
 * Le nom est fixe : un seul passage `e2e:docker` à la fois sur un poste (un second retire le
 * conteneur du premier).
 */
const NAME = "tremplin-e2e-backend";
const repo = resolve(import.meta.dirname, "../../..").replaceAll("\\", "/");
const windows = process.platform === "win32";

const run = [
  // Port publié sur la boucle locale seulement : le back de test reste invisible du réseau.
  `docker run --rm --init --name ${NAME} -p 127.0.0.1:8765:8765`,
  `-v "${repo}:/repo" -v tremplin-devvenv:/opt/venv -v tremplin-uvcache:/root/.cache/uv`,
  "-w /repo/backend --user root -e UV_PROJECT_ENVIRONMENT=/opt/venv -e UV_LINK_MODE=copy",
  "-e PYTHONDONTWRITEBYTECODE=1 --entrypoint uv learning_career_platform-backend:latest",
  "run python -m tests.e2e.server --port 8765 --host 0.0.0.0",
  `--data-dir /tmp/e2e-${Date.now()} --origin http://localhost:5180`,
].join(" ");
const env = {
  ...process.env,
  E2E_DOCKER_NAME: NAME,
  E2E_BACKEND_COMMAND: windows ? run : `exec ${run}`,
};

function removeContainer(): void {
  spawnSync("docker", ["rm", "-f", NAME], { stdio: "ignore" });
}

/** Argument cité pour `cmd.exe` (`pnpm` est un `.cmd` sous Windows, lancé par le shell). */
function quoted(arg: string): string {
  return `"${arg.replaceAll('"', '\\"')}"`;
}

function playwright(args: string[]): number {
  const base = ["exec", "playwright", "test"];
  const result = windows
    ? spawnSync(["pnpm", ...base, ...args.map(quoted)].join(" "), {
        stdio: "inherit",
        shell: true,
        env,
      })
    : spawnSync("pnpm", [...base, ...args], { stdio: "inherit", env });
  return result.status ?? 1;
}

// Ctrl+C arrête Playwright (même console) ; le lanceur, lui, va jusqu'au retrait du conteneur.
process.on("SIGINT", () => {});
removeContainer(); // reste d'un passage interrompu
let status = 1;
try {
  status = playwright(process.argv.slice(2));
} finally {
  removeContainer();
}
process.exit(status);
