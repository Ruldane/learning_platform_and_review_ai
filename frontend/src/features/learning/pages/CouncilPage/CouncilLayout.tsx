import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useCouncilData } from "../../hooks/useCouncilData";
import { useCouncilSession } from "../../hooks/useCouncilSession";
import { useCouncilTabs } from "../../hooks/useCouncilTabs";
import type { GoalOut } from "../../types";
import { CouncilFeed } from "./CouncilFeed";
import { CouncilSide } from "./CouncilSide";
import { CouncilStatus } from "./CouncilStatus";

interface CouncilLayoutProps {
  goal: GoalOut;
  sessionId: string;
  createSocket?: SocketFactory;
}

/**
 * Le Conseil d'un objectif (SPEC 15.2) : barre d'état en haut, débat à gauche (40 %), tableau,
 * sources et propositions à droite (60 %). Un flux abandonné ou une session introuvable se disent
 * ici ; la session se retrouve par l'identifiant de l'objectif (reprise après rechargement).
 */
export function CouncilLayout({ goal, sessionId, createSocket }: CouncilLayoutProps) {
  const navigate = useNavigate();
  const session = useCouncilSession(goal, sessionId, createSocket);
  const data = useCouncilData(goal.id, sessionId, session.stream.events);
  const tabs = useCouncilTabs(session.progress.stage);
  const { stream } = session;

  if (stream.connection === "failed") {
    // Une session introuvable ne se « réessaie » pas : retour aux objectifs.
    const missing = stream.failure === "not_found";
    return (
      <ErrorState
        message={stream.error ?? t("errors.generic")}
        onRetry={missing ? () => void navigate("/apprendre/objectifs") : stream.retry}
        actionLabel={missing ? t("learning.council.goalsLink") : undefined}
      />
    );
  }
  if (stream.connection === "connecting" && stream.events.length === 0) {
    return <LoadingState label={t("learning.council.loading")} />;
  }
  return (
    <div className="flex flex-col gap-4">
      <CouncilStatus session={session} />
      <div className="grid items-start gap-6 lg:grid-cols-[2fr_3fr]">
        <CouncilFeed session={session} onShowProposals={() => tabs.setTab("proposals")} />
        <CouncilSide session={session} data={data} tabs={tabs} />
      </div>
    </div>
  );
}
