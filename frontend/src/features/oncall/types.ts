import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];
export type Incident = Schemas["IncidentView"];
export type ScenarioKind = Incident["kind"];
export type Activity =
  | { kind: "advance" }
  | { kind: "observe"; eventId: string }
  | { kind: "diagnostic" }
  | { kind: "report"; text: string };
