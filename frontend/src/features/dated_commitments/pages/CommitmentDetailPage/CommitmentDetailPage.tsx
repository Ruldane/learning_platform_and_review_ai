import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { detailKey, getCommitment } from "../../api";
import { commitmentsPath } from "../../format";
import { CommitmentContext } from "../CommitmentContext";
import { ObservationForm } from "../ObservationForm";

export function CommitmentDetailPage() {
  const { commitmentId = "" } = useParams<{ commitmentId: string }>();
  const heading = useRef<HTMLHeadingElement>(null);
  const entry = useQuery({
    queryKey: detailKey(commitmentId),
    queryFn: ({ signal }) => getCommitment(commitmentId, signal),
  });
  return (
    <section className="flex max-w-3xl flex-col gap-4">
      <Link to={commitmentsPath} className="self-start underline">
        {t("datedCommitments.back")}
      </Link>
      {entry.isPending && <LoadingState />}
      {entry.isError && (
        <ErrorState message={errorMessage(entry.error)} onRetry={() => void entry.refetch()} />
      )}
      {entry.data && (
        <>
          <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold">
            {entry.data.title}
          </h1>
          <CommitmentContext item={entry.data} />
          {entry.data.status === "due" && (
            <ObservationForm
              key={commitmentId}
              id={commitmentId}
              saved={() => heading.current?.focus()}
            />
          )}
        </>
      )}
    </section>
  );
}
