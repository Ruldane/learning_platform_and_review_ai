import { ApiError } from "@/shared/api/errors";

/**
 * Les champs qu'une 422 du back nomme (`details.fields`, des chemins comme « availability.weekday_minutes »
 * ou « agent_overrides »), sans jamais une valeur. Vide pour toute autre erreur.
 */
export function refusedFields(error: unknown): string[] {
  if (!(error instanceof ApiError) || error.status !== 422) return [];
  const { details } = error;
  if (typeof details !== "object" || details === null || !("fields" in details)) return [];
  const { fields } = details as { fields: unknown };
  return Array.isArray(fields)
    ? fields.filter((field): field is string => typeof field === "string")
    : [];
}

/** Le chemin `field` est-il refusé (lui-même ou un de ses sous-champs) ? */
export const isRefused = (refused: readonly string[], field: string): boolean =>
  refused.some((path) => path === field || path.startsWith(`${field}.`));
