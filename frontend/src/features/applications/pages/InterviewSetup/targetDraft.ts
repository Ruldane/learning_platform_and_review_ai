import type { FreeTarget } from "../../hooks/useStartInterview";

/** What a record-less interview is about: an analysed posting, or a job title. */
export type TargetKind = "posting" | "role";

export interface TargetDraft {
  /** `null`: the default choice (a posting if there is one, otherwise a title). */
  kind: TargetKind | null;
  postingId: string;
  role: string;
}

export const EMPTY_TARGET: TargetDraft = { kind: null, postingId: "", role: "" };

/** The target type that counts: January's choice, else the posting if any can be picked. */
export const kindOf = (draft: TargetDraft, hasPostings: boolean): TargetKind =>
  draft.kind ?? (hasPostings ? "posting" : "role");

/** The target to send, or `null` if the field of this type is still empty. */
export function toTarget(draft: TargetDraft, hasPostings: boolean): FreeTarget | null {
  if (kindOf(draft, hasPostings) === "posting") {
    return draft.postingId === "" ? null : { postingId: draft.postingId };
  }
  const role = draft.role.trim();
  return role === "" ? null : { role };
}
