import { useCallback, useEffect, useRef, useState } from "react";
import type { NoticeView } from "../components/viewTypes";

/** Notifications on screen at once; the next ones wait until one goes away. */
const VISIBLE = 3;

/** The timer of a visible notification, and the time left when it is paused. */
interface Countdown {
  timer: ReturnType<typeof setTimeout> | null;
  left: number;
  since: number;
}

const arm = (left: number, onEnd: () => void): Countdown => ({
  timer: setTimeout(onEnd, left),
  left,
  since: Date.now(),
});

/** The stopped timer, with the time it had left. */
function pause(countdown: Countdown): Countdown {
  clearTimeout(countdown.timer ?? undefined);
  return {
    timer: null,
    left: Math.max(0, countdown.left - (Date.now() - countdown.since)),
    since: 0,
  };
}

/**
 * The notification queue: the first three are on screen, each one goes away on its own after
 * `dismissMs` (the timer starts when visible) or on « Fermer ». `hold(id, true)` pauses
 * its timer (pointer over it, focus inside), `hold(id, false)` resumes it where it was
 * left. All stays in memory.
 */
export function useNoticeQueue(dismissMs: number) {
  const [notices, setNotices] = useState<NoticeView[]>([]);
  const countdowns = useRef(new Map<string, Countdown>());

  const dismiss = useCallback((id: string) => {
    clearTimeout(countdowns.current.get(id)?.timer ?? undefined);
    countdowns.current.delete(id);
    setNotices((previous) => previous.filter((notice) => notice.id !== id));
  }, []);

  const push = useCallback((fresh: NoticeView[]) => {
    setNotices((previous) => [...previous, ...fresh]);
  }, []);

  const hold = useCallback(
    (id: string, held: boolean) => {
      const countdown = countdowns.current.get(id);
      if (!countdown || held === (countdown.timer === null)) return;
      countdowns.current.set(id, held ? pause(countdown) : arm(countdown.left, () => dismiss(id)));
    },
    [dismiss],
  );

  useEffect(() => {
    for (const { id } of notices.slice(0, VISIBLE)) {
      if (!countdowns.current.has(id))
        countdowns.current.set(
          id,
          arm(dismissMs, () => dismiss(id)),
        );
    }
  }, [notices, dismissMs, dismiss]);

  useEffect(() => {
    const pending = countdowns.current;
    return () => {
      pending.forEach(({ timer }) => clearTimeout(timer ?? undefined));
      pending.clear();
    };
  }, []);

  return { notices, push, dismiss, hold };
}
