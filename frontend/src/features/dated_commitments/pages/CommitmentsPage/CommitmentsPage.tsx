import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { getCommitments, listKey } from "../../api";
import { commitmentPath, statuses } from "../../format";
import { CommitmentForm } from "../CommitmentForm";

export function CommitmentsPage() {
  const entries = useQuery({ queryKey: listKey, queryFn: ({ signal }) => getCommitments(signal) });
  return (
    <section className="flex max-w-3xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("datedCommitments.title")}</h1>
      <CommitmentForm />
      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">{t("datedCommitments.history")}</h2>
        {entries.isPending && <LoadingState />}
        {entries.isError && (
          <ErrorState
            message={errorMessage(entries.error)}
            onRetry={() => void entries.refetch()}
          />
        )}
        {entries.data?.length === 0 && <p>{t("datedCommitments.empty")}</p>}
        {entries.data && (
          <ul className="flex flex-col gap-2">
            {entries.data.map((item) => (
              <li key={item.id}>
                <Link className="underline" to={commitmentPath(item.id)}>
                  {item.title}
                </Link>
                {" · "}
                {t(statuses[item.status])}
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
