import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { createIncident, incidentView, listIncidents, runActivity } from "../api";
import type { Activity, ScenarioKind } from "../types";

const lists = ["oncall", "incidents"] as const;
const details = (id: string) => ["oncall", "incident", id] as const;

export function useOncall(id: string) {
  const query = useQuery({ queryKey: lists, queryFn: ({ signal }) => listIncidents(signal) });
  const incident = useQuery({
    queryKey: details(id),
    enabled: !!id,
    queryFn: ({ signal }) => incidentView(id, signal),
    refetchInterval: ({ state }) =>
      state.data?.diagnostic.state === "running" || state.data?.review_state === "running"
        ? 700
        : false,
  });
  const cache = useQueryClient();
  const navigate = useNavigate();
  const start = useMutation({
    mutationFn: (kind: ScenarioKind | null) => createIncident(kind),
    onSuccess: async (created) => {
      cache.setQueryData(details(created.id), created);
      await navigate(`/astreinte/${encodeURIComponent(created.id)}`);
      await cache.invalidateQueries({ queryKey: lists });
    },
  });
  const activity = useMutation({
    mutationFn: (event: Activity) => runActivity(id, event),
    onSettled: async () => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: details(id) }),
        cache.invalidateQueries({ queryKey: lists }),
      ]);
    },
  });
  return { query, incident, start, activity };
}
