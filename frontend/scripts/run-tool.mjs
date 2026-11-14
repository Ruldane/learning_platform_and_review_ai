// Lance les contrôles du front avec node seul, depuis le dossier frontend/, sans passer par pnpm
// (pnpm.exe peut être bloqué par la stratégie de l'hôte ; node, lui, est autorisé).
// Usage : `node frontend/scripts/run-tool.mjs lint|typecheck` (hooks pre-commit du front).
// Mêmes commandes que les scripts `lint` et `typecheck` de package.json : les garder alignés.
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(join(root, "package.json"));
const bin = (pkg, path) => join(dirname(require.resolve(`${pkg}/package.json`)), path);

const TASKS = {
  lint: [[bin("eslint", "bin/eslint.js"), "."]],
  typecheck: [
    [bin("typescript", "bin/tsc"), "--noEmit", "-p", "tsconfig.app.json"],
    [bin("typescript", "bin/tsc"), "--noEmit", "-p", "tsconfig.node.json"],
  ],
};

const steps = TASKS[process.argv[2]];
if (!steps) {
  console.error(`Tâche inconnue : ${process.argv[2] ?? "(aucune)"} (attendu : lint ou typecheck).`);
  process.exit(2);
}
for (const args of steps) {
  const run = spawnSync(process.execPath, args, { cwd: root, stdio: "inherit" });
  if (run.status !== 0) process.exit(run.status ?? 1);
}
