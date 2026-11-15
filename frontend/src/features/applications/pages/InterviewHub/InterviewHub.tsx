import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { InterviewList } from "../../components/InterviewList";
import { useInterviews } from "../../hooks/useInterviews";
import { InterviewSetup } from "../InterviewSetup";
import { InterviewFollow } from "./InterviewFollow";

interface InterviewHubProps {
  /** La fiche dont on voit les entretiens ; `null` : les entretiens sans fiche. */
  applicationId: string | null;
  createSocket?: SocketFactory;
}

interface Followed {
  id: string;
  resumed: boolean;
  /** Suivi depuis son lancement (et non ouvert depuis la liste des entretiens passés). */
  live: boolean;
}

/**
 * Le contenu de la page de l'entretien : l'entretien en cours (suivi, ou repris à l'arrivée), sinon les
 * réglages pour en commencer un et la liste des entretiens passés, dont on ouvre le débrief.
 */
export function InterviewHub({ applicationId, createSocket }: InterviewHubProps) {
  const list = useInterviews(applicationId);
  const [followed, setFollowed] = useState<Followed | null>(null);

  if (list.isPending) return <LoadingState label={t("applications.interviewPage.loading")} />;
  if (list.isError) {
    return <ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} />;
  }
  const running = list.data.find((interview) => interview.status === "running");
  const current = followed ?? (running ? { id: running.id, resumed: false, live: true } : null);
  if (current) {
    return (
      <InterviewFollow
        key={current.id}
        interviewId={current.id}
        resumed={current.resumed}
        live={current.live}
        createSocket={createSocket}
        onClose={() => setFollowed(null)}
      />
    );
  }
  return (
    <div className="flex flex-col gap-6">
      <InterviewSetup
        applicationId={applicationId}
        onStarted={(id, resumed) => setFollowed({ id, resumed, live: true })}
      />
      <section aria-labelledby="past-interviews" className="flex flex-col gap-2">
        <h2 id="past-interviews" className="text-lg font-semibold">
          {t("applications.interviewPage.pastTitle")}
        </h2>
        {list.data.length === 0 ? (
          <p className="text-muted-foreground">{t("applications.interviewPage.pastEmpty")}</p>
        ) : (
          <InterviewList
            interviews={list.data}
            onOpen={(id) => setFollowed({ id, resumed: false, live: false })}
          />
        )}
      </section>
    </div>
  );
}
