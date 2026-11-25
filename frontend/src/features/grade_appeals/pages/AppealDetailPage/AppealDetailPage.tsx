import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { APPEALS, decideAppeal, detailKey, getAppeal, reviewAppeal } from "../../api";
import { AppealActions, type AppealAction } from "./AppealActions";
import { Readings } from "./Readings";

function useAppeal(id: string) {
  return useQuery({
    queryKey: detailKey(id),
    queryFn: ({ signal }) => getAppeal(id, signal),
    refetchInterval: ({ state }) => state.data?.state === "reviewing" ? 750 : false,
  });
}

export function AppealDetailPage() {
  const { appealId = "" } = useParams();
  const row = useAppeal(appealId);
  const queries = useQueryClient();
  const status = useRef<HTMLParagraphElement>(null);
  const command = useMutation({
    mutationFn: async (action: AppealAction) => {
      if (action === "review") await reviewAppeal(appealId);
      else await decideAppeal(appealId, action);
    },
    onSuccess: () => queries.invalidateQueries({ queryKey: APPEALS }),
  });
  return (
    <section className="grid max-w-3xl gap-5">
      <Link className="w-fit underline" to="/skills/appeals">{t("gradeAppeals.back")}</Link>
      {row.isPending ? <LoadingState label={t("gradeAppeals.loading")} /> : null}
      {row.error ? <ErrorState message={errorMessage(row.error)} onRetry={() => void row.refetch()} /> : null}
      {row.data ? <>
        <h1 className="text-2xl font-semibold">{row.data.source.criterion.criterion}</h1>
        <p ref={status} tabIndex={-1} role="status">{t(`gradeAppeals.status.${row.data.state}`)}</p>
        <Readings row={row.data} />
        <AppealActions row={row.data} busy={command.isPending} onAction={(action) => {
          status.current?.focus();
          command.mutate(action);
        }} />
      </> : null}
      {command.error ? <InlineError message={errorMessage(command.error)} /> : null}
    </section>
  );
}
