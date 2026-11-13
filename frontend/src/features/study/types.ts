import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];

export type StudyStart = Schemas["StudyStart"];
export type StudyStarted = Schemas["StudyStarted"];
export type StudySessionOut = Schemas["StudySessionOut"];
export type StudySummaryOut = Schemas["StudySummaryOut"];
export type BlockOut = Schemas["BlockOut"];
export type InterruptOption = Schemas["InterruptOption"];
