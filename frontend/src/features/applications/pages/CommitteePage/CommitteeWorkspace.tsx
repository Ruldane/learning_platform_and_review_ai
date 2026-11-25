import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { CommitteeFollow } from "./CommitteeFollow";

interface CommitteeWorkspaceProps {
  /** The posting judged; `null`: the record is not linked to any analysed posting. */
  postingId: string | null;
  /** The CV version sent with the record (offered first). */
  cvVersionId: string | null;
  createSocket?: SocketFactory;
}

/** A record's committee: without a linked posting there is nothing to judge; otherwise controls and
 * the followed run. */
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
