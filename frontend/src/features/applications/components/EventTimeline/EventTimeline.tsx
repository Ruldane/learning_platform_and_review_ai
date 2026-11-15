import { t } from "@/shared/i18n/t";
import { formatInstant } from "../format";
import type { EventView } from "../viewTypes";

interface EventTimelineProps {
  events: EventView[];
}

function detail(event: EventView): string | null {
  const { statusFrom, statusTo } = event;
  if (event.kind === "status" && statusTo) {
    return statusFrom
      ? t("applications.timeline.statusChange", {
          from: t(`applications.status.${statusFrom}`),
          to: t(`applications.status.${statusTo}`),
        })
      : t("applications.timeline.statusSet", { to: t(`applications.status.${statusTo}`) });
  }
  return event.text;
}

/** Le fil chronologique d'une fiche, du plus ancien au plus récent, chaque ligne datée. */
export function EventTimeline({ events }: EventTimelineProps) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("applications.timeline.empty")}</p>;
  }
  const ordered = [...events].sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
  return (
    <ol
      aria-label={t("applications.timeline.label")}
      className="flex flex-col gap-3 border-l pl-4 text-sm"
    >
      {ordered.map((event) => {
        const text = detail(event);
        return (
          <li key={event.id} className="flex flex-col gap-0.5">
            <span className="font-medium">{t(`applications.timeline.kind.${event.kind}`)}</span>
            <time dateTime={event.at} className="text-xs text-muted-foreground tabular-nums">
              {formatInstant(event.at)}
            </time>
            {text && <span className="break-words">{text}</span>}
          </li>
        );
      })}
    </ol>
  );
}
