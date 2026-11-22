import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { LoadingState } from "@/shared/ui/states/LoadingState";
import { IssuedLink } from "../IssuedLink";
import { ReviewConfirmation } from "../ReviewConfirmation";
import { ShareDetails } from "../ShareDetails";
import { ShareHistory } from "../ShareHistory";
import { ShareSetup } from "../ShareSetup";
import { useMentorReviews } from "./useMentorReviews";

function focus(id: string) {
  requestAnimationFrame(() => document.getElementById(id)?.focus());
}

export function MentorReviewPage() {
  const view = useMentorReviews();
  const { packet, detail, link } = view;
  const busy = [view.prepare, view.issue, view.open, view.revoke].some((item) => item.isPending);
  const error = [view.packets, view.history, view.prepare, view.issue, view.open, view.revoke]
    .find((item) => item.error)?.error;
  return (
    <section className="flex max-w-4xl flex-col gap-5">
      <h1 className="text-2xl font-semibold">{t("mentorReviews.title")}</h1>
      <p className="text-muted-foreground">{t("mentorReviews.intro")}</p>
      {view.packets.data && (
        <ShareSetup packets={view.packets.data} selected={view.packetId} hours={view.hours}
          busy={busy} onPacket={view.setPacketId} onHours={view.setHours}
          onPrepare={() => view.prepare.mutate(view.packetId, { onSuccess: () => focus("mentor-confirm") })} />
      )}
      {packet && <ReviewConfirmation packet={packet} hours={view.hours} busy={busy}
        onConfirm={() => view.issue.mutate({
          packet_id: packet.id, expected_digest: packet.digest, valid_hours: view.hours, confirmed: true,
        }, { onSuccess: () => focus("mentor-link") })} />}
      {link && <IssuedLink key={link.id} url={link.url} />}
      {error && <InlineError message={errorMessage(error)} />}
      {(view.packets.isPending || view.history.isPending) && <LoadingState />}
      {view.history.data && (
        <ShareHistory shares={view.history.data} busy={busy}
          onRead={(id) => view.open.mutate(id, { onSuccess: () => focus("mentor-details") })} />
      )}
      {detail && <ShareDetails share={detail} busy={busy}
        onRevoke={() => view.revoke.mutate(detail.id, { onSuccess: () => focus("mentor-details") })} />}
    </section>
  );
}
