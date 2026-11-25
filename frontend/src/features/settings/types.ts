import type { components } from "@/shared/api/schema";
import type {
  ApiKeyEntry,
  ProviderOption,
  SearchProviderName,
  SearchSettingsView,
} from "./components/viewTypes";

export { PRESET_NAMES, TIERS } from "./components/viewTypes";
export type {
  ApiKeyEntry,
  BraveUsageView,
  KeyTestView,
  PresetMap,
  PresetName,
  ProviderOption,
  SearchProviderName,
  SearchSettingsView,
  Tier,
  TierChoices,
} from "./components/viewTypes";

type Schemas = components["schemas"];

export type AgentOut = Schemas["AgentOut"];
export type ApiKeyOut = Schemas["ApiKeyOut"];
export type BraveUsageOut = Schemas["BraveUsageOut"];
export type SearchUsageOut = Schemas["SearchUsageOut"];
export type KeyTestResult = Schemas["KeyTestResult"];
export type ModelChoice = Schemas["ModelChoice"];
export type ModelsOut = Schemas["ModelsOut"];
export type ProviderModels = Schemas["ProviderModels"];
export type SettingsOut = Schemas["SettingsOut"];
export type UserSettings = Schemas["UserSettings"];

type Assert<T extends true> = T;

/** Checked at compile time: the generated types satisfy the components' display types. */
export type ViewTypesMatchContract = [
  Assert<ApiKeyOut extends ApiKeyEntry ? true : false>,
  Assert<ProviderModels extends ProviderOption ? true : false>,
  // The search settings keep the same provider names as the contract.
  Assert<
    NonNullable<UserSettings["search_provider_order"]> extends SearchProviderName[] ? true : false
  >,
  Assert<
    SearchSettingsView["order"] extends NonNullable<UserSettings["search_provider_order"]>
      ? true
      : false
  >,
];
