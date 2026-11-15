import { useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ErrorState } from "@/shared/ui/states/ErrorState";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { useInterviews } from "../../hooks/useInterviews";
import { usePostingChoices } from "../../hooks/usePostingChoices";
import { InterviewSetup } from "../InterviewSetup";
import { InterviewFollow } from "./InterviewFollow";
import { PastInterviews } from "./PastInterviews";

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
  // Les entretiens refermés : un entretien fini ne se reprend pas tant que la liste le dit « en cours ».
  const [closed, setClosed] = useState<string[]>([]);
  const postings = usePostingChoices(applicationId === null).data;

  if (list.isPending) return <LoadingState label={t("applications.interviewPage.loading")} />;
  if (list.isError) {
    return <ErrorState message={errorMessage(list.error)} onRetry={() => void list.refetch()} />;
  }
  const running = list.data.find((interview) => interview.status === "running");
  // L'entretien en cours trouvé à l'arrivée est suivi pour de bon : sa fin ne le fait pas disparaître.
  if (!followed && running && !closed.includes(running.id)) {
    setFollowed({ id: running.id, resumed: false, live: true });
  }
  const current = followed;
  if (current) {
    return (
      <InterviewFollow
        key={current.id}
        interviewId={current.id}
        resumed={current.resumed}
        live={current.live}
        createSocket={createSocket}
        applicationId={applicationId}
        onClose={() => {
          setClosed([...closed, current.id]);
          setFollowed(null);
        }}
      />
    );
  }
  return (
    <div className="flex flex-col gap-6">
      <InterviewSetup
        applicationId={applicationId}
        onStarted={(id, resumed) => setFollowed({ id, resumed, live: true })}
      />
      <PastInterviews
        interviews={list.data}
        postings={postings ?? []}
        onOpen={(id) => setFollowed({ id, resumed: false, live: false })}
      />
    </div>
  );
}
