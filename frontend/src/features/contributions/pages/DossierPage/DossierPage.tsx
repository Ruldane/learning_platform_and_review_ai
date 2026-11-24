import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { changeDossier, fetchDossier, type DossierCommand } from "../../api";
import { DossierActions } from "./DossierActions";

export function DossierPage() {
  const { id = "" } = useParams();
  const client = useQueryClient();
  const key = ["contributions", "dossier", id] as const;
  const query = useQuery({ queryKey: key, queryFn: ({ signal }) => fetchDossier(id, signal) });
  const save = useMutation({
    mutationFn: (command: DossierCommand) => changeDossier(id, command),
    onSuccess: (saved) => {
      client.setQueryData(key, saved);
      void client.invalidateQueries({ queryKey: ["contributions", "list"] });
    },
  });
  const title = useRef<HTMLHeadingElement>(null);
  const dossier = query.data;
  useEffect(() => {
    if (document.activeElement === document.body) title.current?.focus();
  }, [dossier?.status, dossier?.pull_url]);
  if (query.isPending) return <LoadingState />;
  if (!dossier) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <Link to="/skills/contributions" className="self-start underline">
        {t("contributions.back")}
      </Link>
      <h1 ref={title} tabIndex={-1} className="text-2xl font-semibold">
        {dossier.issue.title}
      </h1>
      <p role="status">{t(`contributions.status.${dossier.status}`)}</p>
      <a href={dossier.issue.url} className="self-start underline" target="_blank" rel="noreferrer">
        {t("contributions.issue", {
          repository: dossier.issue.repository,
          number: dossier.issue.number,
        })}
      </a>
      <p>
        {dossier.chapter} · {dossier.issue.skills.join(", ")}
      </p>
      {dossier.issue.body ? (
        <p className="whitespace-pre-line text-sm">{dossier.issue.body}</p>
      ) : null}
      {save.isError ? <InlineError message={errorMessage(save.error)} /> : null}
      <DossierActions dossier={dossier} pending={save.isPending} act={save.mutate} />
    </div>
  );
}
