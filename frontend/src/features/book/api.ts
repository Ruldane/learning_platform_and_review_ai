import { api, apiBaseUrl } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

function params(programId: string) {
  return { params: { path: { program_id: programId } } };
}

export async function listPrograms(signal: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal }));
}

export async function readBook(programId: string, signal: AbortSignal) {
  return unwrap(await api.GET("/programs/{program_id}/book", { ...params(programId), signal }));
}

export async function requestBook(programId: string) {
  return unwrap(await api.POST("/programs/{program_id}/book", params(programId)));
}

export function downloadLinks(programId: string) {
  const path = `${apiBaseUrl}/api/v1/programs/${encodeURIComponent(programId)}/book`;
  return { pdf: `${path}/pdf`, epub: `${path}/epub` };
}
