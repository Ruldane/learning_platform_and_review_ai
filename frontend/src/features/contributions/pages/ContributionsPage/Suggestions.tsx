import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { createDossier, listSuggestions } from "../../api";

export function Suggestions({ programId }: { programId: string }) {
  const navigate = useNavigate();
  const query = useQuery({
    queryKey: ["contributions", "suggestions", programId],
    queryFn: ({ signal }) => listSuggestions(programId, signal),
  });
  const create = useMutation({
    mutationFn: createDossier,
    onSuccess: (row) => void navigate(`/competences/contributions/${encodeURIComponent(row.id)}`),
  });
  if (query.isPending) return <LoadingState />;
  if (!query.data) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  if (!query.data.items.length) return <p>{t("contributions.empty")}</p>;
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-lg font-medium">
        {query.data.chapter ?? t("contributions.suggestions")}
      </h2>
      {create.isError ? <InlineError message={errorMessage(create.error)} /> : null}
      <ul className="grid gap-3 sm:grid-cols-2">
        {query.data.items.map((issue) => (
          <li key={issue.url} className="flex flex-col items-start gap-2 rounded-lg border p-4">
            <a href={issue.url} target="_blank" rel="noreferrer" className="font-medium underline">
              {issue.title}
            </a>
            <p className="text-sm">
              {issue.repository} · {issue.skills.join(", ")}
            </p>
            <Button
              variant="outline"
              aria-disabled={create.isPending}
              onClick={() => {
                if (!create.isPending)
                  create.mutate({
                    program_id: programId,
                    repository: issue.repository,
                    issue_number: issue.number,
                  });
              }}
            >
              {t("contributions.create")}
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
