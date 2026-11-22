import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type ProfileText = components["schemas"]["LinkedInText"];
export type DraftView = components["schemas"]["LinkedInDraftOut"];

export async function latestDraft(signal: AbortSignal) {
  return unwrap(await api.GET("/linkedin-drafts/latest", { signal }));
}

export async function analyzedOffers(signal: AbortSignal) {
  const rows = unwrap(await api.GET("/postings", { signal }));
  return rows.filter((row) => row.status === "ready" && row.title);
}

export async function prepareDraft(postingId: string) {
  return unwrap(await api.POST("/linkedin-drafts", {
    body: postingId ? { posting_id: postingId } : {},
  }));
}

export async function editDraft(id: string, revision: number, text: ProfileText) {
  return unwrap(await api.PUT("/linkedin-drafts/{draft_id}", {
    params: { path: { draft_id: id } },
    body: { text, revision },
  }));
}
