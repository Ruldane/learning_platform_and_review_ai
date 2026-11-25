import { onLocalReset } from "@/shared/lib/localReset";
import type { TimerState } from "../viewTypes";

/**
 * A session's timer, kept in `sessionStorage`: a page reload or a detour
 * to another page no longer loses the work time. No second is added for the
 * absence (the back end caps it by the real duration anyway). Storage may be refused
 * (private browsing, quota): each access is under `try/catch`, falling back to a new timer.
 */
const TIMER_PREFIX = "study-timer:";
export const timerKey = (studyId: string) => `${TIMER_PREFIX}${studyId}`;

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
    // storage refused: the timer keeps running in memory
  }
}

/** Forgets the timer of a finished or abandoned session. */
export function clearTimer(studyId: string): void {
  try {
    window.sessionStorage.removeItem(timerKey(studyId));
  } catch {
    // nothing to do
  }
}

/** « Tout supprimer »: no timer of a session in the erased space stays in the browser. */
function clearAllTimers(): void {
  try {
    const keys = Array.from({ length: window.sessionStorage.length }, (_, index) =>
      window.sessionStorage.key(index),
    );
    for (const key of keys) {
      if (key?.startsWith(TIMER_PREFIX)) window.sessionStorage.removeItem(key);
    }
  } catch {
    // storage refused: nothing was kept
  }
}

onLocalReset(clearAllTimers);
