import { errorMessage } from "@/shared/api/errors";
import type { ComponentType } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useBrief } from "../../hooks/useBrief";
import { ActivityColumn } from "./ActivityColumn";
import { BriefSections } from "./BriefSections";

/**
 * Home (`/`): the morning brief (seven sections), quick actions and, beside them, the feed
 * of activity. The `pending` advice is followed by its session; « Réessayer » only re-reads a
 * brief that could not be read. `createSocket` and `rereadMs` are for tests only.
 */
export function HomePage({
  createSocket,
  rereadMs,
  Guide,
}: {
  createSocket?: SocketFactory;
  rereadMs?: number;
  Guide?: ComponentType;
}) {
  const { query, brief } = useBrief(createSocket, rereadMs);
  if (query.isPending || (query.isError && !brief)) {
    return (
      <div className="flex flex-col gap-4">
        <h1 className="text-2xl font-semibold">{t("home.brief.title")}</h1>
        <p className="text-muted-foreground">{t("home.brief.subtitle")}</p>
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
      {brief ? <BriefSections brief={brief} guide={Guide ? <Guide /> : null} /> : null}
      <div className="min-w-0">
        <ActivityColumn />
      </div>
    </div>
  );
}
