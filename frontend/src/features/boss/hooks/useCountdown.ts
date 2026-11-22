import { useEffect, useState } from "react";

export function useCountdown(deadline: string, serverTime: string, receivedAt: number) {
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    const interval = window.setInterval(() => setNow(Date.now()), 1_000);
    return () => window.clearInterval(interval);
  }, []);
  const elapsed = Math.max(0, now - receivedAt);
  return Math.max(0, Math.ceil((Date.parse(deadline) - Date.parse(serverTime) - elapsed) / 1_000));
}
