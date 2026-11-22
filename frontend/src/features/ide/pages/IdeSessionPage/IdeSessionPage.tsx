import type { ComponentType } from "react";
import type { IdeGhostProps } from "@/shared/lib/ghostPanels";
import { useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useIdeSession } from "../../hooks/useIdeSession";
import { SessionWorkspace } from "./SessionWorkspace";

interface IdeSessionPageProps {
  /** Pour les tests : le flux de la session du professeur. */
  createSocket?: SocketFactory;
  GhostPanel?: ComponentType<IdeGhostProps>;
}

/**
 * Une séance de code : l'éditeur, la sortie et le professeur côte à côte. La séance est relue toutes
 * les 3 s tant que l'onglet est visible (Claude peut y écrire) ; l'éditeur reste la source de ce qu'on
 * voit et le serveur celle de ce qui est enregistré.
 */
export function IdeSessionPage({ createSocket, GhostPanel }: IdeSessionPageProps) {
  const { sessionId = "" } = useParams();
  const query = useIdeSession(sessionId);
  if (query.data === undefined) {
    if (!query.isError) return <LoadingState label={t("ide.session.loading")} />;
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  // Une relecture en direct qui échoue garde la séance affichée (et ses retouches) : pas d'erreur.
  return (
    <SessionWorkspace
      key={query.data.id}
      session={query.data}
      createSocket={createSocket}
      GhostPanel={GhostPanel}
    />
  );
}
