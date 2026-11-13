import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { SUMMARY_POLL_MS, useStudySession } from "../../hooks/useStudySession";
import { LoadFailed } from "./LoadFailed";
import { StudyEnd } from "./StudyEnd";
import { StudyRunning } from "./StudyRunning";

interface StudySessionPageProps {
  /** Ne sert qu'aux tests (faux WebSocket). */
  createSocket?: SocketFactory;
  /** Intervalle de relecture du bilan, en ms (réduit par les tests). */
  pollMs?: number;
}

/**
 * Une session d'étude (`/etudier/session/:studyId`). Ouverte : le Tuteur, le minuteur et le
 * tableau. Terminée : le bilan (relu jusqu'à `finished` après « Terminer »). Abandonnée ou
 * introuvable : un état vide qui ramène au départ. Une relecture ratée en arrière-plan se dit en
 * ligne, sans remplacer la page (le minuteur reste monté).
 */
export function StudySessionPage({
  createSocket,
  pollMs = SUMMARY_POLL_MS,
}: StudySessionPageProps) {
  const { studyId = "" } = useParams();
  const navigate = useNavigate();
  const [finishing, setFinishing] = useState(false);
  const { query, budget } = useStudySession(studyId, finishing, pollMs);
  const home = () => void navigate("/etudier/session");

  if (query.isPending) return <LoadingState label={t("study.session.loading")} />;
  if (query.isError && query.data === undefined) {
    return <LoadFailed error={query.error} onRetry={() => void query.refetch()} onHome={home} />;
  }
  const session = query.data;
  const failure =
    query.isError && !query.isFetching ? (
      <InlineError message={errorMessage(query.error)} onRetry={() => void query.refetch()} />
    ) : null;
  if (session.status === "finished") return <StudyEnd session={session} />;
  if (session.status === "cancelled") {
    return (
      <EmptyState
        title={t("study.session.cancelledTitle")}
        description={t("study.session.cancelledDescription")}
        action={{ label: t("study.session.newBlock"), onClick: home }}
      />
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {failure}
      <StudyRunning
        key={session.id}
        session={session}
        finishing={finishing}
        onFinishing={() => setFinishing(true)}
        summaryLate={finishing && budget.exhausted}
        onRetrySummary={() => {
          budget.restart();
          void query.refetch();
        }}
        createSocket={createSocket}
      />
    </div>
  );
}
