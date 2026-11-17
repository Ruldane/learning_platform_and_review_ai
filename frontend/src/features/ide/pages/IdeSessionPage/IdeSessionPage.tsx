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
}

/**
 * Une séance de code : l'éditeur, la sortie et le professeur côte à côte. La séance est lue une
 * fois ; ensuite l'éditeur est la source de ce qu'on voit et le serveur celle de ce qui est
 * enregistré.
 */
export function IdeSessionPage({ createSocket }: IdeSessionPageProps) {
  const { sessionId = "" } = useParams();
  const query = useIdeSession(sessionId);
  if (query.isPending) return <LoadingState label={t("ide.session.loading")} />;
  if (query.isError) {
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  return <SessionWorkspace key={query.data.id} session={query.data} createSocket={createSocket} />;
}
