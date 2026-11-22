import type { QueryClient } from "@tanstack/react-query";
import type { Mission } from "./api";

export const missionsKey = ["missions"] as const;

export function saveMission(cache: QueryClient, mission: Mission) {
  cache.setQueryData<Mission[]>(missionsKey, (previous) => {
    if (previous?.some(({ id }) => id === mission.id)) {
      return previous.map((item) =>
        item.id === mission.id && item.revision <= mission.revision ? mission : item,
      );
    }
    return [mission, ...(previous ?? [])];
  });
}
