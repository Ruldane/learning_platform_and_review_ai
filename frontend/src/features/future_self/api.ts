import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { ProjectionQuery } from "./types";

export async function fetchProjection(query: ProjectionQuery, signal: AbortSignal) {
  return unwrap(await api.GET("/future-self", { params: { query }, signal }));
}
