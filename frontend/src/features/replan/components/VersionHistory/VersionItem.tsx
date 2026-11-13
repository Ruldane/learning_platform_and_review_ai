import { t } from "@/shared/i18n/t";
import type { VersionView } from "../viewTypes";

const DAY = new Intl.DateTimeFormat("fr-FR", { dateStyle: "long" });

interface VersionItemProps {
  version: VersionView;
}

/** Une version du plan : numéro, genre, statut en toutes lettres, raison, date et bilan replié. */
export function VersionItem({ version }: VersionItemProps) {
  const changes = version.diff
    ? t("replan.history.changes", {
        added: version.diff.added.length,
        removed: version.diff.removed.length,
        moved: version.diff.moved.length,
      })
    : null;
  return (
    <li className="flex flex-col gap-1 rounded-lg border bg-card px-3 py-2">
      <p className="flex flex-wrap items-baseline gap-x-3">
        <span className="font-semibold">
          {t("replan.history.version", { version: version.version })}
        </span>
        <span className="text-sm text-muted-foreground">
          {t(`replan.history.kind.${version.kind}`)}
        </span>
        <span className="text-sm font-medium">{t(`replan.history.status.${version.status}`)}</span>
      </p>
      {version.reason ? <p className="text-sm">{version.reason}</p> : null}
      <p className="text-sm text-muted-foreground">
        {t("replan.history.created", { date: DAY.format(new Date(version.createdAt)) })}
        {changes ? ` · ${changes}` : ""}
      </p>
      {version.review ? (
        <details className="text-sm">
          <summary className="cursor-pointer font-medium">{t("replan.history.review")}</summary>
          <p className="mt-1 whitespace-pre-line text-muted-foreground">{version.review}</p>
        </details>
      ) : null}
    </li>
  );
}
