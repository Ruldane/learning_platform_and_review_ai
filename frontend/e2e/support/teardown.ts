import { spawnSync } from "node:child_process";

/**
 * Démontage global des parcours : retire le conteneur du back lancé par `pnpm e2e:docker`
 * (`E2E_DOCKER_NAME`). Playwright arrête ses serveurs après ce démontage ; sous Windows, il ne sait
 * que tuer l'arbre des processus, et le client `docker` tué laisse le conteneur tourner (et le
 * tuyau de sortie ouvert : Playwright ne se terminait plus). Un conteneur déjà parti est ignoré.
 */
export default function teardown(): void {
  const name = process.env.E2E_DOCKER_NAME;
  if (!name) return;
  spawnSync("docker", ["rm", "-f", name], { stdio: "ignore" });
}
