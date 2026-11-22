import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { PacketSummary } from "../../api";

interface Props {
  packets: PacketSummary[];
  selected: string;
  hours: number;
  onPacket: (id: string) => void;
  onHours: (hours: number) => void;
  onPrepare: () => void;
  busy: boolean;
}

const control = "min-w-0 rounded-md border border-input bg-background p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function ShareSetup({ packets, selected, hours, onPacket, onHours, onPrepare, busy }: Props) {
  if (!packets.length) return <p>{t("mentorReviews.emptyPackets")}</p>;
  return (
    <form className="flex flex-col gap-3" onSubmit={(event) => { event.preventDefault(); onPrepare(); }}>
      <label className="flex flex-col gap-1.5 text-sm">
        <span>{t("mentorReviews.packet")}</span>
        <select className={control} required value={selected} onChange={(event) => onPacket(event.target.value)}>
          <option value="" disabled>{t("mentorReviews.packet")}</option>
          {packets.map((packet) => <option key={packet.id} value={packet.id}>{packet.title}</option>)}
        </select>
      </label>
      <label className="flex max-w-56 flex-col gap-1.5 text-sm">
        <span>{t("mentorReviews.duration")}</span>
        <input className={control} type="number" min={1} max={168} step={1} required
          value={Number.isFinite(hours) ? hours : ""}
          onChange={(event) => onHours(event.target.valueAsNumber)} />
      </label>
      <Button type="submit" className="self-start" disabled={busy || !selected}>
        {t("mentorReviews.prepare")}
      </Button>
    </form>
  );
}
