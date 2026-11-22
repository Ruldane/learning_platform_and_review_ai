import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type Site = components["schemas"]["SiteOut"];
export type Publication = components["schemas"]["PublicationOut"];
export type Draft = components["schemas"]["PortfolioDraftOut"];
export type Target = "cv" | "kit";

export async function readSite(signal?: AbortSignal) {
  return unwrap(await api.GET("/portfolio", { signal }));
}

export async function buildDraft(selected: string[]) {
  return unwrap(await api.POST("/portfolio/drafts", { body: { selected } }));
}

export async function readPreview(id: string, signal: AbortSignal) {
  return unwrap(
    await api.GET("/portfolio/drafts/{draft_id}/preview", {
      params: { path: { draft_id: id } },
      parseAs: "text",
      signal,
    }),
  );
}

export async function getZip(id: string) {
  return unwrap(
    await api.GET("/portfolio/drafts/{draft_id}/zip", {
      params: { path: { draft_id: id } },
      parseAs: "blob",
    }),
  );
}

export async function publish(draft: Draft, destination: string) {
  return unwrap(
    await api.POST("/portfolio/publish", {
      body: { draft_id: draft.id, digest: draft.digest, destination, confirmed: true },
    }),
  );
}

export async function withdraw(publication: Publication) {
  await api.POST("/portfolio/withdraw", {
    body: { draft_id: publication.revision_id, destination: publication.url, confirmed: true },
  });
}

export async function proposeLink(publication: Publication, target: Target, enabled: boolean) {
  return unwrap(
    await api.PUT("/portfolio/links/{target}", {
      params: { path: { target } },
      body: { revision_id: publication.revision_id, url: publication.url, enabled },
    }),
  );
}
