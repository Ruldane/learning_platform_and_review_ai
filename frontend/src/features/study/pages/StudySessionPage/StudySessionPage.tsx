import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { EmptyState } from "@/shared/ui/states/EmptyState";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { SUMMARY_POLL_MS, useStudySession } from "../../hooks/useStudySession";
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
 * introuvable : un état vide qui ramène au départ.
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
  if (query.isError) {
    if (query.error instanceof ApiError && query.error.status === 404) {
      return (
        <EmptyState
          title={t("study.session.notFoundTitle")}
          description={t("study.session.notFoundDescription")}
          action={{ label: t("study.session.back"), onClick: home }}
        />
      );
    }
    return <ErrorState message={errorMessage(query.error)} onRetry={() => void query.refetch()} />;
  }
  const session = query.data;
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
  );
}
