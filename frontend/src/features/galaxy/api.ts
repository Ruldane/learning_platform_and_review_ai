import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Graph = components["schemas"]["GalaxyView"];
export type Node = components["schemas"]["GalaxyNode"];

export async function readGalaxy(signal?: AbortSignal): Promise<Graph> {
  return unwrap(await api.GET("/galaxy", { signal }));
}
