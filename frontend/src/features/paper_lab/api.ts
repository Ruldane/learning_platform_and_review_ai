import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

export async function listPaperLabs(signal: AbortSignal) {
  return unwrap(await api.GET("/paper-labs", { signal }));
}

export async function openPaperLab(labId: string, signal: AbortSignal) {
  return unwrap(
    await api.GET("/paper-labs/{lab_id}", { params: { path: { lab_id: labId } }, signal }),
  );
}

export async function preparePaperLab(url: string) {
  return unwrap(await api.POST("/paper-labs", { body: { url } }));
}
