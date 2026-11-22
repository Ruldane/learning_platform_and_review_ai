import { useEffect, useState } from "react";
import { ResponseClock } from "./concentration";

export function useResponseClock(enabled: boolean) {
  const [clock] = useState(() => new ResponseClock(() => performance.now()));
  useEffect(() => {
    if (!enabled || document.hidden) clock.interrupt();
    else clock.restart();
    const hidden = () => {
      if (document.hidden) clock.interrupt();
    };
    const blurred = () => clock.interrupt();
    document.addEventListener("visibilitychange", hidden);
    window.addEventListener("blur", blurred);
    return () => {
      document.removeEventListener("visibilitychange", hidden);
      window.removeEventListener("blur", blurred);
    };
  }, [clock, enabled]);
  return clock;
}
