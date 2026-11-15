import { createContext } from "react";
import type { LineView, MasterProfileView } from "../viewTypes";

/** Les erreurs 422 de l'enregistrement : chemin d'un champ (`experiences.2.role`) → message. */
export const FieldErrorsContext = createContext<Record<string, string>>({});

/** Une erreur concerne-t-elle ce chemin ou l'un de ses descendants ? */
export function hasErrorUnder(errors: Record<string, string>, prefix: string): boolean {
  return Object.keys(errors).some((path) => path === prefix || path.startsWith(`${prefix}.`));
}

const LINE_PATH = /^(experiences|education|projects)\.(\d+)\.(achievements|details)\.(\d+)(\..*)?$/;

interface WithLines {
  achievements?: LineView[];
  details?: LineView[];
}

/**
 * Le serveur a reçu le profil nettoyé (lignes vides retirées) : l'indice d'une ligne fautive compte
 * sans elles. Ce chemin le ramène à la ligne affichée, pour que l'erreur se place sous le bon champ.
 */
function displayedPath(sent: MasterProfileView, path: string): string {
  const match = LINE_PATH.exec(path);
  if (!match) return path;
  const [, section, row, list, line, rest = ""] = match;
  const owner: WithLines | undefined = sent[section as "experiences"][Number(row)];
  const shown = (owner?.[list as "achievements"] ?? [])
    .map((item, index) => (item.text.trim() === "" ? -1 : index))
    .filter((index) => index >= 0);
  const index = shown[Number(line)];
  return index === undefined ? path : `${section}.${row}.${list}.${index}${rest}`;
}

/** Les erreurs 422 d'un profil envoyé nettoyé, replacées sur les lignes telles qu'affichées. */
export function displayedErrors(
  sent: MasterProfileView,
  errors: Record<string, string>,
): Record<string, string> {
  return Object.fromEntries(
    Object.entries(errors).map(([path, message]) => [displayedPath(sent, path), message]),
  );
}
