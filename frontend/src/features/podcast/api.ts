import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";
import { runSourceHeaders, type RunSource } from "@/shared/lib/runSource";

export type Episode = components["schemas"]["PodcastEpisodeOut"];
export type CheckResult = components["schemas"]["PodcastQuizOut"];

export async function readPodcast(signal?: AbortSignal) {
  return unwrap(await api.GET("/podcast/today", { signal }));
}

export async function preparePodcast(source?: RunSource) {
  return unwrap(await api.POST("/podcast/today", { headers: runSourceHeaders(source) }));
}

export async function checkPodcast(episodeId: string, choices: number[]) {
  return unwrap(
    await api.POST("/podcast/{episode_id}/quiz", {
      params: { path: { episode_id: episodeId } },
      body: { choices },
    }),
  );
}

export const audioUrl = (id: string) => `${apiBaseUrl}/api/v1/podcast/${id}/audio`;
