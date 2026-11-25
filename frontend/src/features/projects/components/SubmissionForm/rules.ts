import { webUrl } from "@/shared/lib/webUrl";
import { t } from "@/shared/i18n/t";

/** Server limits (`projects/service/rules.py`). The server is the authority; these save a trip. */
export const REPO_URL_MAX = 2048;
export const DESCRIPTION_MAX = 4000;
export const SCREENSHOTS_MAX = 5;
export const SCREENSHOT_BYTES_MAX = 5 * 1024 * 1024;
export const SCREENSHOT_TYPES = ["image/png", "image/jpeg", "image/webp"];

/** The characters of a text as the server counts them: code points, not UTF-16 units. */
export const characterCount = (text: string): number => [...text].length;

export interface SubmissionErrors {
  missing?: string;
  repoUrl?: string;
  description?: string;
}

/** Is a repository link text an http(s) address of 2,048 characters at most? */
function repoUrlIsValid(repoUrl: string): boolean {
  return repoUrl.length <= REPO_URL_MAX && webUrl(repoUrl) !== null;
}

/** Fields to fix: a link or description (at least one), an http(s) link, description ≤ 4,000. */
export function submissionErrors(repoUrl: string, description: string): SubmissionErrors {
  const errors: SubmissionErrors = {};
  if (repoUrl.trim() === "" && description.trim() === "") {
    errors.missing = t("projects.submission.errors.missing");
  }
  if (repoUrl.trim() !== "" && !repoUrlIsValid(repoUrl.trim())) {
    errors.repoUrl = t("projects.submission.errors.repoUrl");
  }
  if (characterCount(description) > DESCRIPTION_MAX) {
    errors.description = t("projects.submission.errors.description");
  }
  return errors;
}

/** Why a screenshot is refused (format, weight), or `null` if it is acceptable. */
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
 * The screenshots kept after a choice: a refused screenshot (format, weight) or one beyond the
 * fifth is never kept, and each cause is reported once.
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
