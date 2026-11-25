import type { TimerState } from "../viewTypes";

/** A new timer: the work phase, running. */
export function initialTimer(workSeconds: number): TimerState {
  return { phase: "work", secondsLeft: workSeconds, workedSeconds: 0, running: true };
}

/**
 * Advances the timer by `elapsed` seconds (the phase changes as soon as its time has run out and
 * the rest moves to the next). Only work adds to `workedSeconds`: the break never
 * counts. A zero or negative duration changes nothing.
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
