import { t } from "@/shared/i18n/t";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import type { VersionView } from "../viewTypes";
import { VersionItem } from "./VersionItem";

interface VersionHistoryProps {
  /** Most recent first, as the back end returns them. */
  versions: VersionView[];
  /** The empty state's action (rule 15.4: never a dead end). */
  emptyAction?: { label: string; onClick: () => void };
}

/** The plan's history: one row per version, with its status, reason and date. */
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
