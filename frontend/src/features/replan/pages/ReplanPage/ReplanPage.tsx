import { useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useVersions } from "../../hooks/useVersions";
import { useWaitingReplan } from "../../hooks/useWaitingReplan";
import { pendingVersion, toVersionView } from "../../toView";
import { ProposalPanel } from "./ProposalPanel";
import { ReplanHistory } from "./ReplanHistory";
import { ReplanRun } from "./ReplanRun";
import { ReplanStart } from "./ReplanStart";

/**
 * Replanification d'un programme (`/apprendre/programme/:programId/replanification`). Sans
 * replanification en cours : le formulaire (heures disponibles, message). Avec une : la
 * proposition (changements, charge avant et après, plafond), le fil du Stratège et la carte pour
 * accepter ou refuser. Une replanification qui attend déjà une réponse est rejointe d'office.
 */
export function ReplanPage({ createSocket }: { createSocket?: SocketFactory }) {
  const { programId = "" } = useParams();
  const versions = useVersions(programId);
  const waiting = useWaitingReplan(programId);
  // `undefined` : on suit la session qui attend (si elle existe) ; `null` : nouvelle demande.
  const [followed, setFollowed] = useState<string | null | undefined>(undefined);
  const sessionId = followed === undefined ? (waiting.data ?? null) : followed;
  const views = useMemo(() => versions.data?.map(toVersionView), [versions.data]);
  const proposal = sessionId && views ? pendingVersion(views) : null;

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("replan.title")}</h1>
        <Link to={`/apprendre/programme/${programId}`} className="text-sm underline">
          {t("replan.back")}
        </Link>
      </header>
      {waiting.isPending ? <LoadingState label={t("replan.loading")} /> : null}
      {waiting.isError ? (
        <ErrorState message={errorMessage(waiting.error)} onRetry={() => void waiting.refetch()} />
      ) : null}
      {proposal ? <ProposalPanel version={proposal} /> : null}
      {waiting.isSuccess && sessionId === null ? (
        <ReplanStart programId={programId} onSession={setFollowed} />
      ) : null}
      {sessionId !== null ? (
        <ReplanRun
          key={sessionId}
          sessionId={sessionId}
          programId={programId}
          onAgain={() => setFollowed(null)}
          createSocket={createSocket}
        />
      ) : null}
      <ReplanHistory
        versions={views}
        loading={versions.isPending}
        error={versions.error}
        onRetry={() => void versions.refetch()}
      />
    </div>
  );
}
