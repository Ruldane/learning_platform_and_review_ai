import { useCallback, useEffect, useRef, useState } from "react";
import type { NoticeView } from "../components/viewTypes";

/** Notifications à l'écran en même temps ; les suivantes attendent que l'une disparaisse. */
const VISIBLE = 3;

/** Le minuteur d'une notification visible, et le temps qui lui reste quand il est en pause. */
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

/** Le minuteur arrêté, avec ce qu'il lui restait. */
function pause(countdown: Countdown): Countdown {
  clearTimeout(countdown.timer ?? undefined);
  return {
    timer: null,
    left: Math.max(0, countdown.left - (Date.now() - countdown.since)),
    since: 0,
  };
}

/**
 * La file des notifications : les trois premières sont à l'écran, chacune disparaît seule après
 * `dismissMs` (le minuteur part quand elle devient visible) ou à « Fermer ». `hold(id, true)` met
 * son minuteur en pause (pointeur dessus, focus dedans), `hold(id, false)` le reprend où il en
 * était. Tout reste en mémoire.
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
