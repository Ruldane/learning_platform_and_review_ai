import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { openLibrary, replayBasePath, replayKey, startReplay } from "../../api";

import { ScenarioCard } from "../../components/ScenarioCard";

export function ReplayPage() {
  const cache = useQueryClient();
  const navigate = useNavigate();
  const library = useQuery({ queryKey: replayKey, queryFn: ({ signal }) => openLibrary(signal) });
  const create = useMutation({
    mutationFn: (scenario: string) => startReplay({ scenario, receipt: crypto.randomUUID() }),
    onSuccess: (item) => {
      void cache.invalidateQueries({ queryKey: replayKey });
      void navigate(`${replayBasePath}/${item.id}`);
    },
  });
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4">
      <h1 className="text-2xl font-semibold">{t("incidentReplay.title")}</h1>
      <p>{t("incidentReplay.intro")}</p>
      {library.isPending && <LoadingState label={t("incidentReplay.loading")} />}
      {library.isError && (
        <ErrorState message={errorMessage(library.error)} onRetry={() => void library.refetch()} />
      )}
      {create.isError && <InlineError message={errorMessage(create.error)} />}
      {library.data?.scenarios.map((scenario) => (
        <ScenarioCard
          key={scenario.key}
          title={scenario.title}
          context={scenario.context}
          pending={create.isPending}
          onStart={() => create.mutate(scenario.key)}
        />
      ))}
      <h2 className="font-semibold">{t("incidentReplay.recent")}</h2>
      {library.data?.history.length === 0 && <p>{t("incidentReplay.empty")}</p>}
      <ul className="list-disc pl-5">
        {library.data?.history.map((item) => (
          <li key={item.id}>
            <Link className="underline" to={`${replayBasePath}/${item.id}`}>
              {item.title}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
