import { useCallback, useEffect, useRef, useState } from "react";
import type { NoticeView } from "../components/viewTypes";

/** Notifications à l'écran en même temps ; les suivantes attendent que l'une disparaisse. */
const VISIBLE = 3;

/**
 * La file des notifications : les trois premières sont à l'écran, chacune disparaît seule après
 * `dismissMs` (le minuteur part quand elle devient visible) ou à « Fermer ». Tout reste en mémoire.
 */
export function useNoticeQueue(dismissMs: number) {
  const [notices, setNotices] = useState<NoticeView[]>([]);
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: string) => {
    clearTimeout(timers.current.get(id));
    timers.current.delete(id);
    setNotices((previous) => previous.filter((notice) => notice.id !== id));
  }, []);

  const push = useCallback((fresh: NoticeView[]) => {
    setNotices((previous) => [...previous, ...fresh]);
  }, []);

  useEffect(() => {
    for (const notice of notices.slice(0, VISIBLE)) {
      if (timers.current.has(notice.id)) continue;
      timers.current.set(
        notice.id,
        setTimeout(() => dismiss(notice.id), dismissMs),
      );
    }
  }, [notices, dismissMs, dismiss]);

  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach((timer) => clearTimeout(timer));
      pending.clear();
    };
  }, []);

  return { notices, push, dismiss };
}
