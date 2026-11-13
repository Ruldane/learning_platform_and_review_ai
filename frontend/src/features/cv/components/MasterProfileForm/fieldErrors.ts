import { createContext } from "react";

/** Les erreurs 422 de l'enregistrement : chemin d'un champ (`experiences.2.role`) → message. */
export const FieldErrorsContext = createContext<Record<string, string>>({});

/** Une erreur concerne-t-elle ce chemin ou l'un de ses descendants ? */
export function hasErrorUnder(errors: Record<string, string>, prefix: string): boolean {
  return Object.keys(errors).some((path) => path === prefix || path.startsWith(`${prefix}.`));
}
