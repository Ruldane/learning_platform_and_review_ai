import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { useRun } from "@/shared/realtime/useRun";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { readExplanation, type FeynmanEntry } from "../../feynmanApi";
import { ExplanationReport } from "./ExplanationReport";
import { ExplanationStart } from "./ExplanationStart";
import { ExplanationTurn } from "./ExplanationTurn";

const openStates = new Set(["running", "waiting_user", "paused"]);

function backPath(entry: FeynmanEntry) {
  if (entry.kind === "lesson") return `/learn/lessons/${encodeURIComponent(entry.id)}`;
  if (entry.kind === "ide") return `/code/${encodeURIComponent(entry.id)}`;
  return "/skills";
}

export function FeynmanThread({ entry }: { entry: FeynmanEntry }) {
  const [starting, setStarting] = useState<string | null>(null);
  const thread = useQuery({
    queryKey: ["feynman", entry.kind, entry.id],
    queryFn: ({ signal }) => readExplanation(entry, signal),
    refetchInterval: ({ state }) =>
      (starting && state.data?.session_id !== starting) || openStates.has(state.data?.status ?? "")
        ? 1500
        : false,
  });
  const row = thread.data;
  const refresh = () => void thread.refetch();
  const pendingStart = starting && row?.session_id !== starting ? starting : null;
  const sessionId = pendingStart ?? (row && openStates.has(row.status) ? row.session_id : null);
  const run = useRun(sessionId, refresh);
  const active = sessionId !== null;
  if (thread.isPending) return <LoadingState />;
  if (thread.isError) return <ErrorState message={errorMessage(thread.error)} onRetry={refresh} />;
  const start = (id: string) => {
    setStarting(id);
    refresh();
  };
  return (
    <>
      <Link to={backPath(entry)} className="self-start text-sm underline underline-offset-4">
        {t(
          entry.kind === "ide"
            ? "feynman.backIde"
            : entry.kind === "lesson"
              ? "feynman.backLesson"
              : "feynman.backSkills",
        )}
      </Link>
      {row && !pendingStart && <p>{row.source.path ?? row.source.title}</p>}
      {row?.report && !active && <ExplanationReport key={row.id} row={row} onSaved={refresh} />}
      {active && <ExplanationTurn run={run} />}
      {row && ["failed", "cancelled", "expired"].includes(row.status) && !active && (
        <p role="status">{t("feynman.interrupted")}</p>
      )}
      {entry.kind !== "saved" && !active && <ExplanationStart entry={entry} onStart={start} />}
    </>
  );
}
