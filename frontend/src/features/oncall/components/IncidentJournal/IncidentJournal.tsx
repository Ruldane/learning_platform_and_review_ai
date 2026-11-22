import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface IncidentJournalProps {
  events: { id: string; minute: number; detail: string }[];
  observed: string[];
  busy: boolean;
  onObserve: (eventId: string) => void;
}

export function IncidentJournal({ events, observed, busy, onObserve }: IncidentJournalProps) {
  return (
    <section className="flex flex-col gap-3" aria-labelledby="oncall-journal">
      <h2 id="oncall-journal" className="text-xl font-semibold">
        {t("oncall.journal")}
      </h2>
      {events.length === 0 && <p className="text-sm">{t("oncall.emptyJournal")}</p>}
      <ol className="divide-y divide-[var(--border)]">
        {events.map((event) => {
          const read = observed.includes(event.id);
          return (
            <li key={event.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <div>
                <p className="text-sm">{t("oncall.minute", { minute: event.minute })}</p>
                <p>{event.detail}</p>
              </div>
              <Button
                variant="secondary"
                aria-pressed={read}
                aria-disabled={read || busy}
                onClick={() => {
                  if (!read && !busy) onObserve(event.id);
                }}
              >
                {t(read ? "oncall.observed" : "oncall.observe", { id: event.id })}
              </Button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
