import type { components } from "@/shared/api/schema";

export * from "./components/viewTypes";

type Schemas = components["schemas"];

/** Les formes du serveur : seules `toView.ts`, `api.ts`, `errors.ts` et les hooks les manipulent. */
export type ProjectSummary = Schemas["ProjectSummary"];
export type ProjectOut = Schemas["ProjectOut"];
export type ProfileEntryIn = Schemas["ProfileEntryIn"];
export type SessionStarted = Schemas["SessionStarted"];
export type DraftKind = Schemas["DraftOut"]["kind"];
