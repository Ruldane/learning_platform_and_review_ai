import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Share } from "../../api";

interface Props {
  shares: Share[];
  onRead: (id: string) => void;
  busy: boolean;
}

export function ShareHistory({ shares, onRead, busy }: Props) {
  return (
    <section className="flex flex-col gap-2" aria-labelledby="mentor-history">
      <h2 id="mentor-history" className="text-lg font-semibold">{t("mentorReviews.history")}</h2>
      {shares.length === 0 ? <p>{t("mentorReviews.emptyShares")}</p> : (
        <ul className="space-y-2">
          {shares.map((share) => (
            <li key={share.id}>
              <Button type="button" variant="outline" disabled={busy}
                className="h-auto min-h-9 max-w-full whitespace-normal break-words"
                onClick={() => onRead(share.id)}>
                <span className="sr-only">{t("mentorReviews.open")} </span>{share.title}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
