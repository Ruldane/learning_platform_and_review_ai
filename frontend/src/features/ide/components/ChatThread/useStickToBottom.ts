import { useLayoutEffect, useRef, useState, type RefObject } from "react";

const NEAR_BOTTOM_PX = 24;

interface Follow {
  /** Le fil est tout en bas : les nouveaux messages l'y gardent. */
  atBottom: boolean;
  /** Le nombre de messages vus quand elle est remontée lire. */
  seen: number;
}

/**
 * Garde le fil au dernier message tant qu'on y est ; remontée lire, il ne bouge plus et
 * `unread` dit qu'il est arrivé des messages (bouton « Nouveaux messages »). `jump` redescend.
 */
export function useStickToBottom(count: number, signal: unknown) {
  const ref: RefObject<HTMLDivElement | null> = useRef(null);
  const [follow, setFollow] = useState<Follow>({ atBottom: true, seen: count });
  useLayoutEffect(() => {
    const el = ref.current;
    if (el && follow.atBottom) el.scrollTop = el.scrollHeight;
  }, [count, signal, follow.atBottom]);

  const onScroll = () => {
    const el = ref.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight <= NEAR_BOTTOM_PX;
    setFollow((prev) => ({
      atBottom,
      seen: atBottom ? count : prev.atBottom ? count : prev.seen,
    }));
  };
  const jump = () => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
    setFollow({ atBottom: true, seen: count });
  };
  return { ref, onScroll, jump, unread: !follow.atBottom && count > follow.seen };
}
