import { Pause, Play } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { formatMinutes } from "@/shared/lib/format";
import { Button } from "@/shared/ui/button";
import type { TimerPhase } from "../viewTypes";
import { TimerFace } from "./TimerFace";
import { useStudyTimer } from "./useStudyTimer";

interface StudyTimerProps {
  workMinutes: number;
  breakMinutes: number;
  /** Temps de travail cumulé, en secondes entières, à chaque seconde gagnée (jamais la pause). */
  onWorkedChange: (seconds: number) => void;
}

function announcementFor(phase: TimerPhase, switches: number, breakMinutes: number): string {
  if (switches === 0) return "";
  return phase === "break"
    ? t("study.timer.announceBreak", { minutes: breakMinutes })
    : t("study.timer.announceWork");
}

/**
 * Minuteur de la session : travail puis pause, en boucle (50 / 10 par défaut), « Mettre en pause »
 * et « Reprendre ». Seul le travail compte. Le changement de phase est annoncé (zone `polite`),
 * jamais le décompte ; la barre n'est animée que si la personne n'a pas demandé moins de mouvement.
 */
export function StudyTimer({ workMinutes, breakMinutes, onWorkedChange }: StudyTimerProps) {
  const workSeconds = Math.max(1, workMinutes) * 60;
  const breakSeconds = Math.max(1, breakMinutes) * 60;
  const { timer, switches, toggle } = useStudyTimer(workSeconds, breakSeconds, onWorkedChange);
  const phaseSeconds = timer.phase === "work" ? workSeconds : breakSeconds;
  const progress = Math.min(100, Math.max(0, 100 - (timer.secondsLeft / phaseSeconds) * 100));
  const Icon = timer.running ? Pause : Play;
  return (
    <section
      aria-label={t("study.timer.label")}
      className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl border bg-card px-4 py-2"
    >
      <TimerFace phase={timer.phase} secondsLeft={timer.secondsLeft} progress={progress} />
      <p className="text-sm tabular-nums text-muted-foreground">
        {t("study.timer.worked", { time: formatMinutes(Math.floor(timer.workedSeconds / 60)) })}
      </p>
      <Button variant="outline" onClick={toggle}>
        <Icon aria-hidden="true" data-icon="inline-start" />
        {timer.running ? t("study.timer.pause") : t("study.timer.resume")}
      </Button>
      {timer.running ? null : (
        <p className="text-sm text-muted-foreground">{t("study.timer.paused")}</p>
      )}
      <p role="status" aria-live="polite" className="sr-only">
        {announcementFor(timer.phase, switches, breakMinutes)}
      </p>
    </section>
  );
}
