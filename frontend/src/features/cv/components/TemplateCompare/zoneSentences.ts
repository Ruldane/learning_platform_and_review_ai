import { t } from "@/shared/i18n/t";
import type { ZoneView } from "../viewTypes";

/** En dessous de cet écart (en points d'encre), une zone n'est pas citée. */
const MIN_GAP_POINTS = 5;
/** Au plus quatre phrases : les plus grands écarts. */
const MAX_SENTENCES = 4;

/** Les écarts de mise en page en phrases françaises, du plus grand au plus petit. */
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
