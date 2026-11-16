import type { components } from "@/shared/api/schema";

export * from "./components/viewTypes";

type Schemas = components["schemas"];

/** Les formes du serveur : seules `toView.ts`, `api.ts`, `errors.ts` et les hooks les manipulent. */
export type RadarRunOut = Schemas["RadarRunOut"];
export type RadarRunSummary = Schemas["RadarRunSummary"];
export type RadarLatestOut = Schemas["RadarLatestOut"];
export type RadarRunIn = Schemas["RadarRunIn"];
export type RunStarted = Schemas["RunStarted"];
