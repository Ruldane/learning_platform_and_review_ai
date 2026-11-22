import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];
export type Dossier = Schemas["ContributionOut"];
export type Suggestion = Schemas["SuggestedIssue"];
type Publication = Schemas["PublicationIn"];

function path(id: string) {
  return { params: { path: { contribution_id: id } } };
}

export async function listPrograms(signal: AbortSignal) {
  return unwrap(await api.GET("/programs", { signal }));
}

export async function listDossiers(signal: AbortSignal) {
  return unwrap(await api.GET("/contributions", { signal }));
}

export async function listSuggestions(programId: string, signal: AbortSignal) {
  return unwrap(
    await api.GET("/contributions/suggestions", {
      params: { query: { program_id: programId } },
      signal,
    }),
  );
}

export async function createDossier(body: Schemas["CreateContribution"]) {
  return unwrap(await api.POST("/contributions", { body }));
}

export async function fetchDossier(id: string, signal: AbortSignal) {
  return unwrap(await api.GET("/contributions/{contribution_id}", { ...path(id), signal }));
}

export type DossierCommand =
  { kind: "confirm"; body: Publication } | { kind: "pull"; url: string } | { kind: "refresh" };

export async function changeDossier(id: string, command: DossierCommand) {
  switch (command.kind) {
    case "confirm":
      return unwrap(
        await api.POST("/contributions/{contribution_id}/publication", {
          ...path(id),
          body: command.body,
        }),
      );
    case "pull":
      return unwrap(
        await api.POST("/contributions/{contribution_id}/pull", {
          ...path(id),
          body: { url: command.url },
        }),
      );
    case "refresh":
      return unwrap(await api.POST("/contributions/{contribution_id}/refresh", path(id)));
  }
}
