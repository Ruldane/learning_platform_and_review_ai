import type { TimerState } from "../viewTypes";

/** Un minuteur neuf : la phase de travail, en marche. */
export function initialTimer(workSeconds: number): TimerState {
  return { phase: "work", secondsLeft: workSeconds, workedSeconds: 0, running: true };
}

/**
 * Fait avancer le minuteur de `elapsed` secondes (la phase change dès que son temps est écoulé et
 * le reste passe à la suivante). Seul le travail s'ajoute à `workedSeconds` : la pause ne compte
 * jamais. Une durée nulle ou négative ne change rien.
 */
export function advance(
  state: TimerState,
  elapsed: number,
  workSeconds: number,
  breakSeconds: number,
): TimerState {
  let { phase, secondsLeft, workedSeconds } = state;
  let remaining = elapsed;
  while (remaining > 0) {
    const step = Math.min(remaining, secondsLeft);
    if (phase === "work") workedSeconds += step;
    secondsLeft -= step;
    remaining -= step;
    if (secondsLeft <= 0) {
      phase = phase === "work" ? "break" : "work";
      secondsLeft = phase === "work" ? workSeconds : breakSeconds;
    }
  }
  return { ...state, phase, secondsLeft, workedSeconds };
}
