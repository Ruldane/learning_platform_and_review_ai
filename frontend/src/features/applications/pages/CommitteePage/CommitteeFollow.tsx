import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useCommittee } from "../../hooks/useCommittee";
import { useCommitteeAnnouncement } from "../../hooks/useCommitteeAnnouncement";
import { useCommittees } from "../../hooks/useCommittees";
import { useCvVersions } from "../../hooks/useCvVersions";
import { useStartCommittee } from "../../hooks/useStartCommittee";
import { useLaunchFocus } from "./useLaunchFocus";
import { CommitteeControls } from "./CommitteeControls";
import { CommitteeRunSection } from "./CommitteeRunSection";

interface CommitteeFollowProps {
  postingId: string;
  cvVersionId: string | null;
  createSocket?: SocketFactory;
}

/**
 * Les commandes et l'exécution suivie : celle que January vient de lancer (ou de reprendre après un
 * 409), sinon la plus récente de l'offre. Quand January lance le comité, le focus passe à la note
 * « le comité délibère » : le bouton qu'elle vient d'activer se grise.
 */
export function CommitteeFollow({ postingId, cvVersionId, createSocket }: CommitteeFollowProps) {
  const committees = useCommittees(postingId);
  const versions = useCvVersions(postingId);
  const start = useStartCommittee(postingId);
  const [followed, setFollowed] = useState<string | null>(null);
  const runId = followed ?? committees.data?.[0]?.id ?? null;
  const run = useCommittee(runId);
  const announcement = useCommitteeAnnouncement(run.data);
  const running = run.data?.status === "running";
  const { note, launch } = useLaunchFocus(running, runId, start.start, setFollowed);

  return (
    <div className="flex flex-col gap-4">
      <p role="status" className="sr-only">
        <span key={announcement.count}>{announcement.message}</span>
      </p>
      <CommitteeControls
        versions={versions.data}
        versionsLoading={versions.isPending}
        defaultVersionId={cvVersionId}
        view={run.data}
        hasRuns={(committees.data?.length ?? 0) > 0 || followed !== null}
        start={start}
        onLaunch={(versionId) => void launch(versionId)}
      />
      {running ? (
        <p ref={note} tabIndex={-1} className="text-sm font-medium outline-none">
          {t("applications.committeeControls.running")}
        </p>
      ) : null}
      <CommitteeRunSection
        committees={committees}
        run={run}
        runId={runId}
        createSocket={createSocket}
      />
    </div>
  );
}
