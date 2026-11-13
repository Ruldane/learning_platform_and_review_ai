import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { VersionView } from "../viewTypes";
import { VersionItem } from "./VersionItem";

interface VersionHistoryProps {
  /** La plus récente d'abord, comme le back les rend. */
  versions: VersionView[];
  /** L'action de l'état vide (règle 15.4 : jamais d'impasse). */
  emptyAction?: { label: string; onClick: () => void };
}

/** L'historique du plan : une ligne par version, avec son statut, sa raison et sa date. */
export function VersionHistory({ versions, emptyAction }: VersionHistoryProps) {
  if (versions.length === 0) {
    return (
      <EmptyState
        title={t("replan.history.empty")}
        description={t("replan.history.emptyHint")}
        action={emptyAction}
      />
    );
  }
  return (
    <ol aria-label={t("replan.history.heading")} className="flex flex-col gap-2">
      {versions.map((version) => (
        <VersionItem key={version.version} version={version} />
      ))}
    </ol>
  );
}
