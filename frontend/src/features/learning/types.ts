import type { components } from "@/shared/api/schema";

export type { GoalInput, GoalRow, GoalStatusView, ProposalView } from "./components/viewTypes";

type Schemas = components["schemas"];

export type GoalOut = Schemas["GoalOut"];
export type GoalStarted = Schemas["GoalStarted"];
export type ProposalOut = Schemas["ProposalOut"];
export type BoardOut = Schemas["BoardOut"];
export type ChooseOut = Schemas["ChooseOut"];
