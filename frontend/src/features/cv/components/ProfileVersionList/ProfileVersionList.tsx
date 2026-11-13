import { t } from "@/shared/i18n/t";
import { formatDay } from "../formatDate";
import type { ProfileVersionView } from "../viewTypes";

interface ProfileVersionListProps {
  /** Dans n'importe quel ordre : la liste montre la plus récente en premier. */
  versions: ProfileVersionView[];
}

function sourceText(source: string): string {
  if (source === "archivist" || source === "january") return t(`cv.versions.source.${source}`);
  return source;
}

/** L'historique du profil maître : numéro, état, origine et jour ; la version en vigueur est signalée. */
export function ProfileVersionList({ versions }: ProfileVersionListProps) {
  if (versions.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("cv.versions.empty")}</p>;
  }
  const sorted = [...versions].sort((a, b) => b.version - a.version);
  const current = sorted.find((version) => version.status === "validated")?.version;
  return (
    <ol aria-label={t("cv.versions.label")} className="flex flex-col gap-2">
      {sorted.map((version) => (
        <li
          key={version.version}
          className="flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-xl border bg-card px-3 py-2 text-sm"
        >
          <span className="font-medium">
            {t("cv.versions.version", { version: version.version })}
          </span>
          <span>{t(`cv.versions.status.${version.status}`)}</span>
          {version.version === current ? (
            <span className="rounded-md bg-primary px-1.5 py-0.5 text-xs font-medium text-primary-foreground">
              {t("cv.versions.current")}
            </span>
          ) : null}
          <span className="text-muted-foreground">{sourceText(version.source)}</span>
          <span className="text-muted-foreground">
            {t("cv.versions.created", { date: formatDay(version.createdAt) })}
          </span>
        </li>
      ))}
    </ol>
  );
}
