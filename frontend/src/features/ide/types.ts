import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];

export type Exercise = Schemas["ExerciseOut"];
export type ExerciseIn = Schemas["ExerciseIn"];
export type ExerciseGenerateIn = Schemas["ExerciseGenerateIn"];
export type IdeSession = Schemas["IdeSessionOut"];
export type SessionSummary = Schemas["SessionSummary"];
export type RunStarted = Schemas["RunOut"];
export type RunProgress = Schemas["RunProgress"];
export type Note = Schemas["NoteOut"];
export type Preferences = Schemas["PreferencesOut"];
export type Usage = Schemas["UsageOut"];
export type TeachIn = Schemas["TeachIn"];
export type TeachOut = Schemas["TeachOut"];

export type RunKind = Schemas["RunIn"]["kind"];
/** D'où vient une exécution ou une note : l'interface (`app`) ou Claude par le MCP (`mcp`). */
export type Origin = Schemas["RunOut"]["origin"];
export type RunStatus = RunProgress["status"];
export type TeacherMode = Preferences["teacher_mode"];
