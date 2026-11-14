import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];

export type PostingOut = Schemas["PostingOut"];
export type PostingSummaryOut = Schemas["PostingSummaryOut"];
export type PostingCreatedOut = Schemas["PostingCreatedOut"];
export type PostingAnalysisOut = Schemas["PostingAnalysisOut"];
export type DuplicateOut = Schemas["DuplicateOut"];
export type GapOut = Schemas["GapOut"];
export type GapRowOut = Schemas["GapRowOut"];
export type TopMissingOut = Schemas["TopMissingOut"];
export type PlanGapStarted = Schemas["PlanGapStarted"];
