import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useBrief } from "../../hooks/useBrief";
import { ActivityColumn } from "./ActivityColumn";
import { BriefSections } from "./BriefSections";

/**
 * L'accueil (`/`) : le brief du matin (sept rubriques), les actions rapides et, à côté, le fil
 * d'activité. Le conseil `pending` est suivi par sa session ; « Réessayer » ne sert qu'à relire un
 * brief qui n'a pas pu être lu. `createSocket` et `rereadMs` ne servent qu'aux tests.
 */
export function HomePage({
  createSocket,
  rereadMs,
}: {
  createSocket?: SocketFactory;
  rereadMs?: number;
}) {
  const { query, brief } = useBrief(createSocket, rereadMs);
  if (query.isPending || (query.isError && !brief)) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-semibold">{t("home.brief.title")}</h1>
        {query.isPending ? (
          <LoadingState label={t("home.loading")} />
        ) : (
          <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
        )}
      </div>
    );
  }
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      {brief ? <BriefSections brief={brief} /> : null}
      <div className="min-w-0">
        <ActivityColumn />
      </div>
    </div>
  );
}
