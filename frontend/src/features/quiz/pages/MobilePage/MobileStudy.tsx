import { useRef } from "react";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { MobileSnapshot } from "../../mobile/data";
import { pendingReviews } from "../../mobile/storage";
import { MobileBrief } from "./MobileBrief";
import { MobileCardReview } from "./MobileCardReview";
import { MobileSettings } from "./MobileSettings";
import { useMobileReview } from "./useMobileReview";

export function MobileStudy({ snapshot, pinned, offline }: {
  snapshot: MobileSnapshot;
  pinned: boolean;
  offline: boolean;
}) {
  const { answer, sync, synchronize } = useMobileReview(snapshot.owner, pinned, offline);
  const status = useRef<HTMLParagraphElement>(null);
  const pending = pinned ? pendingReviews(snapshot.owner) : [];
  const card = snapshot.cards.find((item) =>
    !pending.some((entry) => entry.card === item.id && entry.due === item.due));
  const error = answer.error ?? sync.error;
  return (
    <>
      <MobileBrief snapshot={snapshot} />
      {!offline ? <MobileSettings snapshot={snapshot} pinned={pinned} /> : null}
      <p ref={status} role="status" tabIndex={-1} className="text-sm">
        {pinned ? t("mobile.pinned") : null}
        {pending.length ? " " + t("mobile.queue", { count: pending.length }) : null}
        {sync.data?.sent ? " " + t("mobile.synced", { count: sync.data.sent }) : null}
        {sync.data?.skipped ? " " + t("mobile.skipped", { count: sync.data.skipped }) : null}
      </p>
      {error ? <InlineError message={errorMessage(error)} /> : null}
      {!offline && pending.length && error ? (
        <Button className="self-start" variant="outline" onClick={() => synchronize(snapshot.owner)}>
          {t("mobile.sync")}
        </Button>
      ) : null}
      <h2 className="text-lg font-semibold">{t("mobile.reviews")}</h2>
      {card ? <MobileCardReview key={card.id} card={card} busy={answer.isPending || sync.isPending}
        answer={(result) => {
          status.current?.focus();
          answer.mutate({ card, result });
        }} /> : <p>{t("mobile.empty")}</p>}
    </>
  );
}
