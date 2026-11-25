import { useState } from "react";
import type { KitView } from "../../types";

/**
 * The kit session the page follows: the one January just started or resumed (409), or
 * the one the server says is open. It is kept until the page ends: the stream that brings the
 * end of session arrives after the server stopped saying « en cours ».
 */
export function useFollowedSession(kit: KitView, started: string | null): string | null {
  const [followed, setFollowed] = useState<string | null>(null);
  const incoming = started ?? (kit.running ? kit.sessionId : null);
  if (incoming && incoming !== followed) setFollowed(incoming);
  return followed;
}
