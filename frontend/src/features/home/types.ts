import type { components } from "@/shared/api/schema";

export * from "./components/viewTypes";

type Schemas = components["schemas"];

/** Les formes du serveur : seules `toView.ts`, `api.ts` et les hooks les manipulent. */
export type BriefOut = Schemas["BriefOut"];
export type ActivityItem = Schemas["ActivityItem"];
export type ActivityPage = Schemas["ActivityPage"];
