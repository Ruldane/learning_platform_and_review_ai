import type { FreeTarget } from "../../hooks/useStartInterview";

/** Sur quoi porte un entretien sans fiche : une offre analysée, ou un intitulé de poste. */
export type TargetKind = "posting" | "role";

export interface TargetDraft {
  /** `null` : le choix par défaut (une offre s'il y en a, sinon un intitulé). */
  kind: TargetKind | null;
  postingId: string;
  role: string;
}

export const EMPTY_TARGET: TargetDraft = { kind: null, postingId: "", role: "" };

/** Le type de cible qui compte : le choix de January, sinon l'offre si elle a des offres à choisir. */
export const kindOf = (draft: TargetDraft, hasPostings: boolean): TargetKind =>
  draft.kind ?? (hasPostings ? "posting" : "role");

/** La cible à envoyer, ou `null` si le champ de ce type est encore vide. */
export function toTarget(draft: TargetDraft, hasPostings: boolean): FreeTarget | null {
  if (kindOf(draft, hasPostings) === "posting") {
    return draft.postingId === "" ? null : { postingId: draft.postingId };
  }
  const role = draft.role.trim();
  return role === "" ? null : { role };
}
