import { ApiError } from "@/shared/api/errors";

/**
 * The fields that a 422 from the back end names (`details.fields`, paths such as
 * « availability.weekday_minutes » or « agent_overrides »), never a value. Empty for any
 * autre erreur.
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

/** Is the path `field` refused (itself or one of its sub-fields)? */
export const isRefused = (refused: readonly string[], field: string): boolean =>
  refused.some((path) => path === field || path.startsWith(`${field}.`));
