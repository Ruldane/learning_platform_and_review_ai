import type { components } from "@/shared/api/schema";

type Schemas = components["schemas"];

export type McpSettings = Schemas["McpSettingsOut"];
export type McpFeatureOut = Schemas["McpFeatureOut"];
export type McpActionOut = Schemas["McpActionOut"];
export type McpTokenOut = Schemas["McpTokenOut"];
export type McpTokenCreated = Schemas["McpTokenCreated"];
export type McpTokenCreateIn = Schemas["McpTokenCreateIn"];
export type McpConfirmationOut = Schemas["McpConfirmationOut"];
export type McpCallOut = Schemas["McpCallOut"];
export type McpChangeOut = Schemas["McpChangeOut"];

export type Decision = "confirm" | "refuse";
