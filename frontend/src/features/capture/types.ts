import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];

export type CaptureRequest = Schemas["CaptureRequest"];
export type JournalPage = Schemas["JournalPage"];
export type JournalEntryOut = Schemas["JournalEntryOut"];
export type JournalKind = JournalEntryOut["kind"];
