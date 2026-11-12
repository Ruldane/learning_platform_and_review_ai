import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];

export type LessonOut = Schemas["LessonOut"];
export type LessonSummaryOut = Schemas["LessonSummaryOut"];
export type ResourceOut = Schemas["ResourceOut"];
export type ProgramSummaryOut = Schemas["ProgramSummaryOut"];
export type LessonStatus = LessonOut["status"];

export type {
  LessonView,
  LibraryFilterValue,
  ProgramOption,
  ResourceStatus,
  ResourceType,
  ResourceView,
} from "./components/viewTypes";
