import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface QueryPanelProps<T> {
  query: UseQueryResult<T>;
  /** The text announced while loading. */
  loading?: string;
  children: (data: T) => ReactNode;
}

/**
 * Loading, an error with « Réessayer », then the content. A failed reread keeps the
 * data already shown (the map rereads every 30 s: an outage does not empty it).
 */
export function QueryPanel<T>({ query, loading, children }: QueryPanelProps<T>) {
  if (query.data !== undefined) return <>{children(query.data)}</>;
  if (query.isError) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  return <LoadingState label={loading ?? t("skills.page.panelLoading")} />;
}
