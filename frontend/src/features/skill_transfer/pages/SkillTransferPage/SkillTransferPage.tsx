import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { listProofs, listTransfers, scheduleTransfer, type Transfer } from "../../api";
import { ScheduleForm } from "../../components/ScheduleForm";
import { PROOFS, TRANSFERS } from "../../queryKeys";
import { proofChoice } from "../../toView";
import { TransferRow } from "./TransferRow";

function refreshInterval(rows: Transfer[] | undefined): number | false {
  if (rows?.some((row) => !row.retry && ["preparing", "grading"].includes(row.stage))) return 750;
  return rows?.some((row) => !row.available) ? 30_000 : false;
}

export function SkillTransferPage() {
  const [search] = useSearchParams();
  const skillId = (search.get("skill") ?? search.get("competence")) || undefined;
  const queries = useQueryClient();
  const proofs = useQuery({
    queryKey: [...PROOFS, skillId],
    queryFn: ({ signal }) => listProofs(skillId, signal),
  });
  const rows = useQuery({
    queryKey: [...TRANSFERS, skillId],
    queryFn: ({ signal }) => listTransfers(skillId, signal),
    refetchInterval: ({ state }) => refreshInterval(state.data),
  });
  const schedule = useMutation({
    mutationFn: scheduleTransfer,
    onSuccess: () => queries.invalidateQueries({ queryKey: TRANSFERS }),
  });
  return (
    <section className="grid max-w-3xl gap-5">
      <h1 className="text-2xl font-semibold">{t("skillTransfer.title")}</h1>
      {skillId ? (
        <Link className="w-fit underline" to="/skills/transfer">
          {t("skillTransfer.all")}
        </Link>
      ) : null}
      {proofs.isPending || rows.isPending ? <LoadingState label={t("skillTransfer.loading")} /> : null}
      {proofs.error ? <ErrorState message={errorMessage(proofs.error)} onRetry={() => void proofs.refetch()} /> : null}
      {proofs.data ? (
        <ScheduleForm
          proofs={proofs.data.map(proofChoice)}
          busy={schedule.isPending}
          onSchedule={(proofId, dueOn) => {
            const proof = proofs.data?.find((item) => item.id === proofId);
            if (proof) schedule.mutate({ skill_id: proof.skill_id, proof_id: proofId, due_on: dueOn });
          }}
        />
      ) : null}
      {schedule.error ? <InlineError message={errorMessage(schedule.error)} /> : null}
      {schedule.isSuccess ? <p role="status">{t("skillTransfer.scheduled")}</p> : null}
      <h2 className="text-lg font-semibold">{t("skillTransfer.history")}</h2>
      {rows.error ? <ErrorState message={errorMessage(rows.error)} onRetry={() => void rows.refetch()} /> : null}
      {rows.data?.length === 0 ? <p>{t("skillTransfer.empty")}</p> : null}
      {rows.data?.length ? (
        <ul className="grid gap-3">
          {rows.data.map((row) => <TransferRow key={row.id} row={row} />)}
        </ul>
      ) : null}
    </section>
  );
}
