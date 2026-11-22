import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { ShareDetail } from "../../api";

const WHEN = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });
const STATUS = {
  active: "mentorReviews.statusActive",
  expired: "mentorReviews.statusExpired",
  revoked: "mentorReviews.statusRevoked",
} as const;

interface Props {
  share: ShareDetail;
  onRevoke: () => void;
  busy: boolean;
}

export function ShareDetails({ share, onRevoke, busy }: Props) {
  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border p-4"
      aria-labelledby="mentor-details">
      <h2 id="mentor-details" tabIndex={-1} className="text-lg font-semibold">{share.title}</h2>
      <p role="status">{t(STATUS[share.status])}</p>
      <p>{t("mentorReviews.expires", { date: WHEN.format(new Date(share.expires_at)) })}</p>
      {share.status === "active" && (
        <Button type="button" variant="outline" onClick={onRevoke} disabled={busy} className="self-start">
          {t("mentorReviews.revoke")}
        </Button>
      )}
      <h3 className="font-semibold">{t("mentorReviews.comments")}</h3>
      {share.comments.length === 0 ? <p>{t("mentorReviews.emptyComments")}</p> : (
        <ul className="space-y-2">
          {share.comments.map((comment) => (
            <li key={comment.id} className="rounded-md border border-border p-3">
              <p className="whitespace-pre-wrap break-words">{comment.text}</p>
              {comment.reviewed && <p className="text-sm">{t("mentorReviews.reviewed")}</p>}
              <p className="mt-1 break-all text-sm text-muted-foreground">
                {t("proofPackets.identifier")} · {comment.proof_id}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
