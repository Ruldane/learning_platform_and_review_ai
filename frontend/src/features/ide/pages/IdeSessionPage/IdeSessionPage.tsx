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
  /** For tests: the teacher session's stream. */
  createSocket?: SocketFactory;
  GhostPanel?: ComponentType<IdeGhostProps>;
}

/**
 * A code session: the editor, the output and the teacher side by side. The session is re-read every
 * 3 s while the tab is visible (Claude can write to it); the editor stays the source of what we
 * see, and the server the source of what is saved.
 */
export function IdeSessionPage({ createSocket, GhostPanel }: IdeSessionPageProps) {
  const { sessionId = "" } = useParams();
  const query = useIdeSession(sessionId);
  if (query.data === undefined) {
    if (!query.isError) return <LoadingState label={t("ide.session.loading")} />;
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  // A failed live re-read keeps the session shown (and its edits): no error.
  return (
    <SessionWorkspace
      key={query.data.id}
      session={query.data}
      createSocket={createSocket}
      GhostPanel={GhostPanel}
    />
  );
}
