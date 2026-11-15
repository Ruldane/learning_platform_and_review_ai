import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { CommitteeFollow } from "./CommitteeFollow";

interface CommitteeWorkspaceProps {
  applicationId: string;
  /** L'offre jugée ; `null` : la fiche n'est liée à aucune offre analysée. */
  postingId: string | null;
  /** La version de CV envoyée avec la fiche (proposée en premier). */
  cvVersionId: string | null;
  createSocket?: SocketFactory;
}

/** Le comité d'une fiche : sans offre liée il n'y a rien à juger ; sinon commandes et exécution suivie. */
export function CommitteeWorkspace({
  postingId,
  cvVersionId,
  createSocket,
}: CommitteeWorkspaceProps) {
  if (postingId === null) {
    return <p className="max-w-prose">{t("applications.committeePage.noPosting")}</p>;
  }
  return (
    <CommitteeFollow postingId={postingId} cvVersionId={cvVersionId} createSocket={createSocket} />
  );
}
