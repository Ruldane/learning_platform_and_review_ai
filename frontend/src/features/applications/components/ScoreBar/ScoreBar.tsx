import { t } from "@/shared/i18n/t";
import type { ScoreKeyView } from "../viewTypes";

const MAX_SCORE = 5;

interface ScoreBarProps {
  name: ScoreKeyView;
  /** La note, de 1 à 5 ; `null` : pas de note rendue. */
  value: number | null;
}

/** Une note du débrief : son nom et « 4 sur 5 » en toutes lettres, et une barre qui ne fait que l'illustrer. */
export function ScoreBar({ name, value }: ScoreBarProps) {
  const share = value === null ? 0 : Math.max(0, Math.min(1, value / MAX_SCORE));
  return (
    <li className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-medium">{t(`applications.debrief.scoreLabel.${name}`)}</span>
        <span>
          {value === null
            ? t("applications.debrief.scoreMissing")
            : t("applications.debrief.score", { value })}
        </span>
      </div>
      <div
        data-testid="score-bar"
        aria-hidden="true"
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full rounded-full bg-primary" style={{ width: `${share * 100}%` }} />
      </div>
    </li>
  );
}
