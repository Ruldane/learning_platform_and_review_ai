import { t } from "@/shared/i18n/t";
import type { ZoneView } from "../viewTypes";

/** Below this gap (in ink points), a zone is not cited. */
const MIN_GAP_POINTS = 5;
/** At most four sentences: the largest gaps. */
const MAX_SENTENCES = 4;

/** Layout gaps as French sentences, from largest to smallest. */
export function zoneSentences(zones: ZoneView[]): string[] {
  return zones
    .map((zone) => ({ zone, points: Math.round((zone.render - zone.original) * 100) }))
    .filter(({ points }) => Math.abs(points) > MIN_GAP_POINTS)
    .sort((a, b) => Math.abs(b.points) - Math.abs(a.points))
    .slice(0, MAX_SENTENCES)
    .map(({ zone, points }) =>
      t(points < 0 ? "cv.template.zoneLess" : "cv.template.zoneMore", {
        n: Math.abs(points),
        place: t(`cv.template.place.${zone.zone}`),
      }),
    );
}
