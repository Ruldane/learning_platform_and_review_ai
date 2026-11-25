import { useEffect, useRef, useState } from "react";
import type { TimerState } from "../viewTypes";
import { advance, initialTimer } from "./timer";
import { readTimer, writeTimer } from "./timerStorage";

const TICK_MS = 1000;
/**
 * What a clock tick can add, in seconds. A background tab is slowed (one
 * tick per minute at most): a minute still passes; a computer left asleep, however, does not
 * count hours of work.
 */
const MAX_STEP_SECONDS = 60;

interface Model {
  timer: TimerState;
  /** Number of phase changes: used to announce the last one. */
  switches: number;
}

/**
 * The session timer: work then break, in a loop, running from display. The gap
 * is read from the clock (not counted in ticks) and capped; a break stops everything.
 * `onWorkedChange` gets the work time, in whole seconds, on each second gained. With
 * `storageKey`, the state is kept in `sessionStorage` and resumed on mount. `halted`
 * stops the clock without touching the person's choice (the Tutor's session stopped).
 */
export function useStudyTimer(
  workSeconds: number,
  breakSeconds: number,
  onWorkedChange: (seconds: number) => void,
  { storageKey, halted = false }: { storageKey?: string; halted?: boolean } = {},
) {
  const [model, setModel] = useState<Model>(() => ({
    timer: readTimer(storageKey) ?? initialTimer(workSeconds),
    switches: 0,
  }));
  const lastTick = useRef(0);
  const reported = useRef(0);
  const running = model.timer.running && !halted;
  const worked = Math.floor(model.timer.workedSeconds);

  useEffect(() => {
    writeTimer(storageKey, model.timer);
  }, [storageKey, model.timer]);

  useEffect(() => {
    if (!running) return;
    lastTick.current = Date.now();
    const id = setInterval(() => {
      const now = Date.now();
      const elapsed = Math.min(MAX_STEP_SECONDS, (now - lastTick.current) / 1000);
      lastTick.current = now;
      setModel((prev) => {
        const timer = advance(prev.timer, elapsed, workSeconds, breakSeconds);
        return { timer, switches: prev.switches + (timer.phase === prev.timer.phase ? 0 : 1) };
      });
    }, TICK_MS);
    return () => clearInterval(id);
  }, [running, workSeconds, breakSeconds]);

  useEffect(() => {
    if (worked === reported.current) return;
    reported.current = worked;
    onWorkedChange(worked);
  }, [worked, onWorkedChange]);

  const toggle = () =>
    setModel((prev) => ({ ...prev, timer: { ...prev.timer, running: !prev.timer.running } }));
  return { timer: { ...model.timer, running }, switches: model.switches, toggle };
}
