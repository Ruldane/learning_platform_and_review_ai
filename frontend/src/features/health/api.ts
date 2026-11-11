import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

/** `GET /health` : toujours 200, le champ `status` dit si tout va bien. */
export async function fetchHealth(signal?: AbortSignal) {
  return unwrap(await api.GET("/health", { signal }));
}
