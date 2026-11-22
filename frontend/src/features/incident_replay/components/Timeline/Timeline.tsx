import { t } from "@/shared/i18n/t";

interface TimelineEntry {
  minute: number;
  title: string;
  observed: string;
}

interface Props {
  events: readonly TimelineEntry[];
  position: number;
  onSeek: (position: number) => void;
}

export function Timeline({ events, position, onSeek }: Props) {
  return (
    <section className="grid gap-3">
      <label className="grid gap-1">
        {t("incidentReplay.timeline")}
        <input
          className="w-full max-w-lg"
          type="range"
          min={0}
          max={events.length - 1}
          value={position}
          aria-valuetext={t("incidentReplay.minute", { value: events[position]?.minute ?? 0 })}
          onChange={(event) => onSeek(Number(event.target.value))}
        />
      </label>
      <ol className="grid gap-2">
        {events.slice(0, position + 1).map((item) => (
          <li className="rounded border p-3" key={item.minute}>
            <span className="text-sm text-muted-foreground">
              {t("incidentReplay.minute", { value: item.minute })}
            </span>
            <h2 className="font-medium">{item.title}</h2>
            <p>{item.observed}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
