import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";

const params = (id: string) => ({ path: { program_id: id } });

export async function readBoss(id: string, signal?: AbortSignal) {
  return unwrap(await api.GET("/boss/programs/{program_id}", { params: params(id), signal }));
}

export async function startBoss(id: string) {
  return unwrap(await api.POST("/boss/programs/{program_id}", { params: params(id) }));
}

export async function submitBoss(id: string) {
  return unwrap(await api.POST("/boss/programs/{program_id}/submit", { params: params(id) }));
}
