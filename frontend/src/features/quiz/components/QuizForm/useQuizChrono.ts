import { useEffect, useState } from "react";

const MAX_ELAPSED_MS = 24 * 60 * 60 * 1000;

export function useQuizChrono(visible: boolean) {
  const [start] = useState(() => performance.now());
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!visible) return undefined;
    const timer = window.setInterval(() => setElapsed(Math.floor(performance.now() - start)), 1000);
    return () => window.clearInterval(timer);
  }, [start, visible]);
  return {
    elapsed,
    readElapsed() {
      const ms = Math.floor(performance.now() - start);
      return ms <= MAX_ELAPSED_MS ? ms : undefined;
    },
  };
}
