import { useState } from "react";
import type { KitView } from "../../types";

/**
 * La session du kit que la page suit : celle que January vient de lancer ou de reprendre (409), ou
 * celle que le serveur dit ouverte. On la garde jusqu'à la fin de la page : le flux qui apporte la
 * fin de session arrive après que le serveur a cessé de dire « en cours ».
 */
export function useFollowedSession(kit: KitView, started: string | null): string | null {
  const [followed, setFollowed] = useState<string | null>(null);
  const incoming = started ?? (kit.running ? kit.sessionId : null);
  if (incoming && incoming !== followed) setFollowed(incoming);
  return followed;
}
