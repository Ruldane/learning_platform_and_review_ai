// Vérifie que src/shared/api/schema.d.ts correspond à contracts/openapi.json : régénère les types
// dans un fichier temporaire avec la même commande que `pnpm gen:api`, puis compare.
// Usage : `pnpm gen:api:check` (hook pre-commit `api-types`). Code de sortie 1 si différent.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const contract = resolve(root, "../contracts/openapi.json");
const schema = resolve(root, "src/shared/api/schema.d.ts");
const require = createRequire(import.meta.url);
const cli = join(dirname(require.resolve("openapi-typescript/package.json")), "bin/cli.js");

const dir = mkdtempSync(join(tmpdir(), "tremplin-api-types-"));
const fresh = join(dir, "schema.d.ts");
const normalize = (path) => readFileSync(path, "utf8").replace(/\r\n/g, "\n");
try {
  execFileSync(process.execPath, [cli, contract, "-o", fresh], { stdio: "ignore" });
  if (normalize(fresh) !== normalize(schema)) {
    console.error(
      "src/shared/api/schema.d.ts n'est pas à jour avec contracts/openapi.json : " +
        "lancer `pnpm --dir frontend gen:api`.",
    );
    process.exitCode = 1;
  }
} finally {
  rmSync(dir, { recursive: true, force: true });
}
