import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];

export type QuizOut = Schemas["QuizOut"];
export type QuizSummaryOut = Schemas["QuizSummaryOut"];
export type QuizStarted = Schemas["QuizStarted"];
export type QuestionOut = Schemas["QuestionOut"];
export type AttemptOut = Schemas["AttemptOut"];
export type AttemptSummaryOut = Schemas["AttemptSummaryOut"];
export type FlashcardOut = Schemas["FlashcardOut"];
export type DueQueue = Schemas["DueQueue"];
export type ReviewOut = Schemas["ReviewOut"];
export type ProgramSummaryOut = Schemas["ProgramSummaryOut"];
