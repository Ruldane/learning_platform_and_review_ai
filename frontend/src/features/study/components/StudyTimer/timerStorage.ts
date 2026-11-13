import type { TimerState } from "../viewTypes";

/**
 * Le minuteur d'une session, gardé dans `sessionStorage` : un rechargement de la page ou un détour
 * par une autre page ne fait plus perdre le temps de travail. Aucune seconde n'est ajoutée pour
 * l'absence (le back borne de toute façon par la durée réelle). Le stockage peut être refusé
 * (navigation privée, quota) : chaque accès est sous `try/catch`, avec repli sur un minuteur neuf.
 */
export const timerKey = (studyId: string) => `study-timer:${studyId}`;

function isTimer(value: unknown): value is TimerState {
  const v = value as Partial<TimerState> | null;
  return (
    typeof v === "object" &&
    v !== null &&
    (v.phase === "work" || v.phase === "break") &&
    typeof v.secondsLeft === "number" &&
    Number.isFinite(v.secondsLeft) &&
    v.secondsLeft >= 0 &&
    typeof v.workedSeconds === "number" &&
    Number.isFinite(v.workedSeconds) &&
    v.workedSeconds >= 0 &&
    typeof v.running === "boolean"
  );
}

export function readTimer(key: string | undefined): TimerState | null {
  if (!key) return null;
  try {
    const raw = window.sessionStorage.getItem(key);
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    return isTimer(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

export function writeTimer(key: string | undefined, timer: TimerState): void {
  if (!key) return;
  try {
    window.sessionStorage.setItem(key, JSON.stringify(timer));
  } catch {
    // stockage refusé : le minuteur continue en mémoire
  }
}

/** Oublie le minuteur d'une session terminée ou abandonnée. */
export function clearTimer(studyId: string): void {
  try {
    window.sessionStorage.removeItem(timerKey(studyId));
  } catch {
    // rien à faire
  }
}
