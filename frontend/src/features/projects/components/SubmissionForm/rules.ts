import { webUrl } from "@/shared/lib/webUrl";
import { t } from "@/shared/i18n/t";

/** Les limites du serveur (`projects/service/rules.py`) : il reste l'autorité, ces gardes évitent un aller-retour. */
export const REPO_URL_MAX = 2048;
export const DESCRIPTION_MAX = 4000;
export const SCREENSHOTS_MAX = 5;
export const SCREENSHOT_BYTES_MAX = 5 * 1024 * 1024;
export const SCREENSHOT_TYPES = ["image/png", "image/jpeg", "image/webp"];

export interface SubmissionErrors {
  missing?: string;
  repoUrl?: string;
  description?: string;
}

/** Le texte d'un lien de dépôt est-il une adresse http(s) de 2 048 caractères au plus ? */
function repoUrlIsValid(repoUrl: string): boolean {
  return repoUrl.length <= REPO_URL_MAX && webUrl(repoUrl) !== null;
}

/** Les champs à corriger : au moins un lien ou une description, un lien http(s), une description ≤ 4 000. */
export function submissionErrors(repoUrl: string, description: string): SubmissionErrors {
  const errors: SubmissionErrors = {};
  if (repoUrl.trim() === "" && description.trim() === "") {
    errors.missing = t("projects.submission.errors.missing");
  }
  if (repoUrl.trim() !== "" && !repoUrlIsValid(repoUrl.trim())) {
    errors.repoUrl = t("projects.submission.errors.repoUrl");
  }
  if (description.length > DESCRIPTION_MAX) {
    errors.description = t("projects.submission.errors.description");
  }
  return errors;
}

/** Pourquoi une capture est refusée (format, poids), ou `null` si elle est recevable. */
export function screenshotProblem(file: File): string | null {
  if (!SCREENSHOT_TYPES.includes(file.type)) {
    return t("projects.submission.errors.format", { name: file.name });
  }
  if (file.size > SCREENSHOT_BYTES_MAX) {
    return t("projects.submission.errors.size", { name: file.name });
  }
  return null;
}

/**
 * Les captures gardées après un choix : une capture refusée (format, poids) ou au-delà de la
 * cinquième n'est jamais gardée, et chaque cause est signalée une fois.
 */
export function pickScreenshots(
  current: File[],
  picked: File[],
): { kept: File[]; problems: string[] } {
  const kept = [...current];
  const problems: string[] = [];
  for (const file of picked) {
    const problem = screenshotProblem(file);
    if (problem) {
      problems.push(problem);
    } else if (kept.length >= SCREENSHOTS_MAX) {
      const tooMany = t("projects.submission.errors.tooMany");
      if (!problems.includes(tooMany)) problems.push(tooMany);
    } else {
      kept.push(file);
    }
  }
  return { kept, problems };
}
