import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Packet } from "../../api";
import { ProofCopy } from "../ProofCopy";

interface Props {
  packet: Packet;
  hours: number;
  busy: boolean;
  onConfirm: () => void;
}

export function ReviewConfirmation({ packet, hours, busy, onConfirm }: Props) {
  const valid = Number.isInteger(hours) && hours >= 1 && hours <= 168;
  return (
    <section aria-labelledby="mentor-confirm" className="flex flex-col gap-3">
      <h2 id="mentor-confirm" tabIndex={-1} className="text-lg font-semibold">
        {t("mentorReviews.review")}
      </h2>
      {valid && <p>{t("mentorReviews.validFor", { hours })}</p>}
      <ProofCopy manifest={packet.manifest} digest={packet.digest} />
      <Button type="button" className="self-start" onClick={onConfirm} disabled={busy || !valid}>
        {t("mentorReviews.confirm")}
      </Button>
    </section>
  );
}
