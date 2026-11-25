import { t } from "@/shared/i18n/t";
import type { ScoreKeyView } from "../viewTypes";

const MAX_SCORE = 5;

interface ScoreBarProps {
  name: ScoreKeyView;
  /** The score, from 1 to 5; `null`: no score given. */
  value: number | null;
}

/** A debrief score: its name and « 4 sur 5 » in words, and a bar that only illustrates it. */
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
