import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { createCase, listCases, options, RECRUITMENTS } from "../../api";
import { RecruitmentForm } from "../../components/RecruitmentForm";

const ROOT = "/career/recruitment-process";

export function RecruitmentListPage() {
  const navigate = useNavigate();
  const queries = useQueryClient();
  const available = useQuery({ queryKey: ["recruitment-options"], queryFn: ({ signal }) => options(signal) });
  const rows = useQuery({ queryKey: RECRUITMENTS, queryFn: ({ signal }) => listCases(signal) });
  const creation = useMutation({
    mutationFn: createCase,
    onSuccess: async (row) => {
      await queries.invalidateQueries({ queryKey: RECRUITMENTS });
      void navigate(`${ROOT}/${row.id}`);
    },
  });
  return (
    <section className="grid max-w-3xl gap-5">
      <h1 className="text-2xl font-semibold">{t("recruitmentProcess.title")}</h1>
      {available.isPending || rows.isPending ? <LoadingState label={t("recruitmentProcess.loading")} /> : null}
      {available.error ? <ErrorState message={errorMessage(available.error)} onRetry={() => void available.refetch()} /> : null}
      {available.data ? (
        <RecruitmentForm {...available.data} busy={creation.isPending} onCreate={(posting, project) => {
          creation.mutate({ posting_id: posting, project_id: project });
        }} />
      ) : null}
      {creation.error ? <InlineError message={errorMessage(creation.error)} /> : null}
      <h2 className="text-lg font-semibold">{t("recruitmentProcess.listing")}</h2>
      {rows.error ? <ErrorState message={errorMessage(rows.error)} onRetry={() => void rows.refetch()} /> : null}
      {rows.data?.length === 0 ? <p>{t("recruitmentProcess.empty")}</p> : null}
      {rows.data?.length ? (
        <ul className="grid gap-3">
          {rows.data.map((row) => (
            <li key={row.id} className="grid gap-1 rounded-xl border bg-card p-4">
              <Link className="font-medium underline" to={`${ROOT}/${row.id}`}>{row.posting_title}</Link>
              <p className="text-sm">{t(`recruitmentProcess.status.${row.state}`)}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
