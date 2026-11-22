import { t } from "@/shared/i18n/t";
import { GhostMetrics } from "./GhostMetrics";
import type { Metrics, Reference } from "./viewTypes";

export function ComparisonBody({
  kind,
  selected,
  current,
  ongoing,
}: {
  kind: "ide" | "quiz";
  selected: Reference;
  current: Metrics | null;
  ongoing?: boolean;
}) {
  const comparable = selected.version === "same";
  return (
    <>
      <div className="grid gap-2 md:grid-cols-2">
        <GhostMetrics title={t("ghost.reference")} kind={kind} values={selected.metrics} />
        {kind === "ide" && ongoing && (
          <div className="rounded-lg border px-3 py-2">
            <h3 className="mb-1 font-medium">{t("ghost.current")}</h3>
            <p role="status">{t("ghost.inProgress")}</p>
          </div>
        )}
        {comparable && current && (
          <GhostMetrics
            title={t(ongoing ? "ghost.current" : "ghost.completed")}
            kind={kind}
            values={current}
            ticking={ongoing && kind === "quiz"}
          />
        )}
      </div>
      {!comparable && (
        <p>{t(selected.version === "changed" ? "ghost.changedVersion" : "ghost.unknownVersion")}</p>
      )}
      {comparable && ongoing && kind === "quiz" && <p>{t("ghost.pace")}</p>}
    </>
  );
}
