import type { UseQueryResult } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";

interface QueryPanelProps<T> {
  query: UseQueryResult<T>;
  /** Le texte annoncé pendant le chargement. */
  loading?: string;
  children: (data: T) => ReactNode;
}

/**
 * Chargement, erreur avec « Réessayer », puis le contenu. Une relecture qui échoue garde les
 * données déjà affichées (la carte se relit toutes les 30 s : une coupure ne la vide pas).
 */
export function QueryPanel<T>({ query, loading, children }: QueryPanelProps<T>) {
  if (query.data !== undefined) return <>{children(query.data)}</>;
  if (query.isError) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  return <LoadingState label={loading ?? t("skills.page.panelLoading")} />;
}
