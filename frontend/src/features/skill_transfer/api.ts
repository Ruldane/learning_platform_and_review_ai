import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Transfer = components["schemas"]["TransferOut"];
export type Proof = components["schemas"]["ProofOption"];
type TransferIn = components["schemas"]["TransferIn"];

export async function listProofs(skillId: string | undefined, signal: AbortSignal) {
  return unwrap(
    await api.GET("/skill-transfers/proofs", { params: { query: { skill_id: skillId } }, signal }),
  );
}

export async function listTransfers(skillId: string | undefined, signal: AbortSignal) {
  return unwrap(
    await api.GET("/skill-transfers", { params: { query: { skill_id: skillId } }, signal }),
  );
}

export async function scheduleTransfer(body: TransferIn) {
  return unwrap(await api.POST("/skill-transfers", { body }));
}

export async function prepareTransfer(id: string) {
  return unwrap(
    await api.POST("/skill-transfers/{transfer_id}/prepare", {
      params: { path: { transfer_id: id } },
    }),
  );
}

export async function answerTransfer(id: string, answer: string) {
  return unwrap(
    await api.POST("/skill-transfers/{transfer_id}/answer", {
      params: { path: { transfer_id: id } },
      body: { answer },
    }),
  );
}
