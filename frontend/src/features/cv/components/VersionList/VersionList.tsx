import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { formatDay } from "../formatDate";
import type { VersionView } from "../viewTypes";

interface VersionListProps {
  /** In any order: the list shows the most recent first. */
  versions: VersionView[];
  onOpen: (versionId: string) => void;
}

function pagesText(count: number | null): string | null {
  if (count === null) return null;
  return count === 1 ? t("cv.cvVersions.pages.one") : t("cv.cvVersions.pages.many", { count });
}

/** A version opens only if its PDF exists; a generation in progress or failed does not. */
const canOpen = (version: VersionView): boolean =>
  version.status === "ready" || version.status === "pages_exceeded";

/** The CV versions of a posting, most recent first: status, pages, day, file, « Ouvrir ». */
export function VersionList({ versions, onOpen }: VersionListProps) {
  if (versions.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("cv.cvVersions.empty")}</p>;
  }
  const sorted = [...versions].sort((a, b) => b.number - a.number);
  return (
    <ol aria-label={t("cv.cvVersions.label")} className="flex flex-col gap-2">
      {sorted.map((version) => {
        const pages = pagesText(version.pageCount);
        return (
          <li
            key={version.id}
            className="flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-xl border bg-card px-3 py-2 text-sm"
          >
            <span className="font-medium">
              {t("cv.cvVersions.version", { number: version.number })}
            </span>
            <span>{t(`cv.cvVersions.status.${version.status}`)}</span>
            {pages ? <span>{pages}</span> : null}
            <span className="text-muted-foreground">
              {t("cv.cvVersions.created", { date: formatDay(version.createdAt) })}
            </span>
            <span className="break-all text-muted-foreground">{version.filename}</span>
            {version.status === "failed" && version.failureReason ? (
              <span className="basis-full text-muted-foreground">{version.failureReason}</span>
            ) : null}
            {canOpen(version) ? (
              <Button
                variant="outline"
                size="sm"
                className="ml-auto"
                aria-label={t("cv.cvVersions.openNamed", { number: version.number })}
                onClick={() => onOpen(version.id)}
              >
                {t("cv.cvVersions.open")}
              </Button>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
