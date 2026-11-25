import { useLayoutEffect, useRef, useState, type RefObject } from "react";

const NEAR_BOTTOM_PX = 24;

interface Follow {
  /** The thread is at the very bottom: new messages keep it there. */
  atBottom: boolean;
  /** The number of messages seen when the user scrolled back up to read. */
  seen: number;
}

/**
 * Keeps the thread on the last message as long as the user is there. When scrolling up to read,
 * the thread stays put and `unread` flags new messages (« Nouveaux messages »). `jump` goes down.
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
