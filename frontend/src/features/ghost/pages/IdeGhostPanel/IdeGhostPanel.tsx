import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { IdeGhostProps } from "@/shared/lib/ghostPanels";
import { InlineError } from "@/shared/ui/states/InlineError";
import { fetchIdeGhost } from "../../api";
import { GhostComparison, type Metrics } from "../../components/GhostComparison";

import { toReference } from "../../toView";

function metrics(current: IdeGhostProps["current"]): Metrics | null {
  if (!current || current.status === "running") return null;
  const passed =
    current.status === "done" && current.exitCode !== null ? current.exitCode === 0 : null;
  return {
    duration: current.elapsedMs,
    errors: passed === null ? null : Number(!passed),
    completed: passed === null ? null : Number(passed),
    total: passed === null ? null : 1,
  };
}

export function IdeGhostPanel({ sessionId, current }: IdeGhostProps) {
  const [params, setParams] = useSearchParams();
  const selectedId = params.get("ghost") ?? params.get("fantome");
  const completed = current && current.status !== "running" ? current.id : null;
  const query = useQuery({
    queryKey: ["ghost", "ide", sessionId, selectedId, completed],
    queryFn: ({ signal }) => fetchIdeGhost(sessionId, selectedId, signal),
    placeholderData: (previous) => previous,
  });
  if (query.isPending)
    return (
      <p role="status" className="text-sm">
        {t("ghost.loading")}
      </p>
    );
  if (!query.data) {
    return <InlineError message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  const attempts = query.data.filter((item) => item.id !== current?.id).map(toReference);
  return (
    <GhostComparison
      kind="ide"
      attempts={attempts}
      selected={attempts.find((item) => item.id === selectedId)}
      onSelect={(id) => {
        const updated = new URLSearchParams(params);
        if (id) updated.set("fantome", id);
        else updated.delete("fantome");
        void setParams(updated, { replace: true, preventScrollReset: true });
      }}
      current={metrics(current)}
      ongoing={current?.status === "running"}
    />
  );
}
