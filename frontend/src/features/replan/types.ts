import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];

export type PlanVersionOut = Schemas["PlanVersionOut"];
export type VersionDiffOut = Schemas["VersionDiffOut"];
export type WeekLoadOut = Schemas["WeekLoadOut"];
export type ReplanRequest = Schemas["ReplanRequest"];
