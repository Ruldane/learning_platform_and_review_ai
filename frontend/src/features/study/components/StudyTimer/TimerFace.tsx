import { t } from "@/shared/i18n/t";
import type { TimerPhase } from "../viewTypes";

function clock(totalSeconds: number): string {
  const seconds = Math.max(0, Math.ceil(totalSeconds));
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

interface TimerFaceProps {
  phase: TimerPhase;
  secondsLeft: number;
  /** Avancement de la phase, de 0 à 100. */
  progress: number;
}

/** Phase en cours, temps restant (jamais annoncé seconde par seconde) et barre d'avancement. */
export function TimerFace({ phase, secondsLeft, progress }: TimerFaceProps) {
  return (
    <>
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {t(`study.timer.phase.${phase}`)}
        </p>
        <p
          role="timer"
          aria-label={t("study.timer.remaining")}
          className="text-2xl font-semibold tabular-nums"
        >
          {clock(secondsLeft)}
        </p>
      </div>
      <div aria-hidden="true" className="h-1.5 min-w-24 flex-1 overflow-hidden rounded bg-muted">
        <div
          className="h-full bg-primary motion-safe:transition-[width] motion-safe:duration-200"
          style={{ width: `${progress}%` }}
        />
      </div>
    </>
  );
}
