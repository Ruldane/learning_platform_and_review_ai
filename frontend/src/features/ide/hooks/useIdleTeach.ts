import { useEffect, useRef } from "react";

/** Idle time on one line before offering help (option, off by default). */
export const IDLE_MS = 30_000;

interface IdleOptions {
  /** The option is checked in the preferences. */
  enabled: boolean;
  /** The cursor line; `null` until the learner has touched anything. */
  line: number | null;
  /** Changes on each keystroke: typing restarts from zero, without ever calling the teacher. */
  activity: number;
  onIdle: () => void;
}

/**
 * A 30 s timer: if the option is checked and the cursor stays on the same line without
 * typing, `onIdle` fires **once**; moving or typing rearms it. Option off: no
 * minuterie n'existe.
 */
export function useIdleTeach({ enabled, line, activity, onIdle }: IdleOptions) {
  const latest = useRef(onIdle);
  useEffect(() => {
    latest.current = onIdle;
  });
  useEffect(() => {
    if (!enabled || line === null) return undefined;
    const timer = setTimeout(() => latest.current(), IDLE_MS);
    return () => clearTimeout(timer);
  }, [enabled, line, activity]);
}
