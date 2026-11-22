import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { createInvestigation, investigationsKey, investigationsPath, readLibrary } from "../../api";

export function InvestigationLibrary() {
  const cache = useQueryClient();
  const navigate = useNavigate();
  const library = useQuery({
    queryKey: investigationsKey,
    queryFn: ({ signal }) => readLibrary(signal),
  });
  const create = useMutation({
    mutationFn: createInvestigation,
    onSuccess: (item) => {
      void cache.invalidateQueries({ queryKey: investigationsKey });
      void navigate(`${investigationsPath}/${item.id}`);
    },
  });
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4">
      <h1 className="text-2xl font-semibold">{t("dataInvestigation.title")}</h1>
      <p>{t("dataInvestigation.intro")}</p>
      {library.isPending && <LoadingState label={t("dataInvestigation.loading")} />}
      {library.isError && (
        <ErrorState message={errorMessage(library.error)} onRetry={() => void library.refetch()} />
      )}
      {create.isError && <InlineError message={errorMessage(create.error)} />}
      {library.data?.cases.map((item) => (
        <section className="grid gap-2 rounded border p-3" key={item.key} aria-label={item.title}>
          <h2 className="font-semibold">{item.title}</h2>
          <p>{item.brief}</p>
          <Button disabled={create.isPending} onClick={() => create.mutate(item.key)}>
            {t("dataInvestigation.start")}
          </Button>
        </section>
      ))}
      <h2 className="font-semibold">{t("dataInvestigation.recent")}</h2>
      {library.data?.history.length === 0 && <p>{t("dataInvestigation.empty")}</p>}
      <ul className="list-disc pl-5">
        {library.data?.history.map((item) => (
          <li key={item.id}>
            <Link className="underline" to={`${investigationsPath}/${item.id}`}>
              {item.title}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
