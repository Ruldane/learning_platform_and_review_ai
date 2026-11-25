import { t } from "@/shared/i18n/t";
import { ignoredCount } from "../../toView";
import type { VersionOut } from "../../types";

const pagesLabel = (count: number): string =>
  count === 1 ? t("cv.cvVersions.pages.one") : t("cv.cvVersions.pages.many", { count });

/** Page count of the generated CV, then of the original; without a count, only the comparison. */
export function exceededText(version: VersionOut): string {
  const original = pagesLabel(version.original_page_count);
  return version.page_count
    ? t("cv.reviewPage.pagesExceeded", { count: pagesLabel(version.page_count), original })
    : t("cv.reviewPage.pagesExceededUnknown", { original });
}

/** Accepted changes the template cannot place: never shown as applied. */
export function ignoredText(version: VersionOut): string | null {
  const count = ignoredCount(version);
  if (count === 0) return null;
  return count === 1
    ? t("cv.reviewPage.ignoredNote.one")
    : t("cv.reviewPage.ignoredNote.many", { count });
}
