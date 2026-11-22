import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { PacketSummary } from "../../api";

interface Props {
  entries: PacketSummary[];
  onOpen: (id: string) => void;
  busy: boolean;
}

export function PacketHistory({ entries, onOpen, busy }: Props) {
  return (
    <section className="flex flex-col gap-2" aria-labelledby="proof-history">
      <h2 id="proof-history" className="text-lg font-semibold">{t("proofPackets.history")}</h2>
      {entries.length === 0 ? <p>{t("proofPackets.noHistory")}</p> : (
        <ul className="space-y-2">
          {entries.map((item) => (
            <li key={item.id}>
              <Button type="button" variant="outline" disabled={busy}
                className="h-auto min-h-9 max-w-full whitespace-normal break-words"
                onClick={() => onOpen(item.id)}>
                <span className="sr-only">{t("proofPackets.open")} </span>{item.title}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
