/**
 * Display types for the feature's components. Components may not import
 * `types.ts` nor `shared/api` (splitting rule): they therefore describe here, structurally, what
 * they receive. `types.ts` checks at compile time that the generated types satisfy them.
 */

export const TIERS = ["fast", "standard", "strong", "vision"] as const;
export type Tier = (typeof TIERS)[number];

export const PRESET_NAMES = ["all_haiku", "haiku_sonnet_strong", "all_glm", "all_openai"] as const;
export type PresetName = (typeof PRESET_NAMES)[number];

export interface ModelChoice {
  provider: string;
  model: string;
}

/** The model chosen for each of the four levels. */
export type TierChoices = Record<Tier, ModelChoice>;

export type PresetMap = Record<PresetName, TierChoices>;

/** A provider offered in the dropdowns (`models` null: free-text entry). */
export interface ProviderOption {
  name: string;
  label: string;
  has_key: boolean;
  models: string[] | null;
}

/** A key as displayed: never in clear, only the last 4 characters. */
export interface ApiKeyEntry {
  provider: string;
  label: string;
  source: "ui" | "env" | null;
  last4: string | null;
  readable: boolean;
  last_test_ok: boolean | null;
}

export interface KeyTestView {
  ok: boolean;
  message: string;
}

/** Search languages offered, in display order (ISO 639-1 codes). */
export const SEARCH_LANGUAGES = ["fr", "en", "es", "de", "it", "pt"] as const;
export type SearchLanguage = (typeof SEARCH_LANGUAGES)[number];

export type SearchProviderName = "searxng" | "brave";

/** Web search settings as the components edit them. */
export interface SearchSettingsView {
  languages: string[];
  preferred: string[];
  excluded: string[];
  order: SearchProviderName[];
  maxQueries: number;
  maxPages: number;
}

/** Brave usage for the calendar month (`month`: "AAAA-MM", in UTC). */
export interface BraveUsageView {
  hasKey: boolean;
  used: number;
  cap: number;
  month: string;
}

/**
 * The availability durations as `AvailabilityFields` edits them (text while being typed).
 * saisie).
 */
export interface AvailabilityValues {
  weekday: string;
  weekendMin: string;
  weekendMax: string;
}

export type AvailabilityKey = keyof AvailabilityValues;

/**
 * Which durations are out of bounds; `weekendOrder`: the weekend minimum exceeds its maximum.
 */
export interface AvailabilityFlags {
  weekday: boolean;
  weekendMin: boolean;
  weekendMax: boolean;
  weekendOrder: boolean;
}

/**
 * An agent from `GET /settings/agents`; `tier` null: an override remains for an agent the
 * server no longer knows.
 */
export interface AgentRow {
  name: string;
  tier: Tier | null;
}

/** Model overrides per agent (agent name to its model). */
export type AgentOverrides = Record<string, ModelChoice | undefined>;

/** What a PDF file field kept: the file, or the reason it was refused. */
export interface PdfChoice {
  file: File | null;
  problem: string | null;
}

/** The two PDFs of the CV step, kept by the page (see `useCvDocuments`). */
export interface CvDocuments {
  cv: PdfChoice;
  linkedin: PdfChoice;
  setCv: (choice: PdfChoice) => void;
  setLinkedin: (choice: PdfChoice) => void;
}
