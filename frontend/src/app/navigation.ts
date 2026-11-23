import { BookOpen, Brain, Briefcase, Code2, FlaskConical, Home, Settings } from "lucide-react";
import { navigation } from "@/shared/i18n/messages/navigation";
import type { MessageKey } from "@/shared/i18n/t";
import type { FeatureManifest, NavEntry } from "@/shared/lib/feature";
import type { NavGroup, NavItem } from "./buildNav";

const SECTIONS = [
  { section: "home", path: "/", labelKey: "nav.home", icon: Home, color: "var(--section-home)" },
  { section: "learn", path: "/etudier", labelKey: "navigation.learn", icon: BookOpen, color: "var(--section-learn)" },
  { section: "code", path: "/coder", labelKey: "navigation.code", icon: Code2, color: "var(--section-study)" },
  { section: "memory", path: "/cerveau", labelKey: "navigation.memory", icon: Brain, color: "var(--section-memory)" },
  { section: "career", path: "/carriere", labelKey: "nav.career", icon: Briefcase, color: "var(--section-career)" },
  { section: "lab", path: "/labo", labelKey: "navigation.lab", icon: FlaskConical, color: "var(--section-skills)" },
  { section: "settings", path: "/reglages", labelKey: "nav.settings", icon: Settings, color: "var(--section-settings)" },
] as const;

export type Section = (typeof SECTIONS)[number]["section"];
export type Hub = Exclude<Section, "home" | "settings" | "lab">;
export type SettingsArea = keyof typeof navigation.settings;
type Feature = keyof typeof navigation.features;

export interface Destination extends NavItem {
  id: Feature;
  section: Section;
  description: MessageKey;
  modelsRequired: boolean;
  settingsArea?: SettingsArea;
}

const PRIMARY: Partial<Record<Feature, Section>> = {
  home: "home",
  health: "home",
  learning: "learn",
  program: "learn",
  lessons: "learn",
  study: "learn",
  quiz: "learn",
  conversations: "learn",
  capture: "learn",
  boss: "learn",
  lesson_hunt: "learn",
  lesson_updates: "learn",
  replan: "learn",
  ghost: "learn",
  ide: "code",
  projects: "code",
  code_trial: "code",
  brain: "memory",
  memory: "memory",
  reading_stack: "memory",
  skills: "career",
  cv: "career",
  applications: "career",
  gap: "career",
  radar: "career",
  compatible_offers: "career",
  account: "settings",
  auth: "settings",
  calendar: "settings",
  costs: "settings",
  mcp: "settings",
  message_review: "settings",
  routines: "settings",
  settings: "settings",
  surprise_interview: "settings",
};

const AREAS: Record<string, SettingsArea> = {
  "/reglages/modeles": "models",
  "/reglages/mcp": "access",
  "/reglages/revision-messagerie": "access",
  "/reglages/disponibilite": "profile",
  "/reglages/agenda": "profile",
  "/reglages/style": "profile",
  "/reglages/etude": "profile",
  "/reglages/entretien-surprise": "profile",
};

const NEEDS_MODELS = new Set<Feature>([
  "book", "contradictory_watch", "expert_debates", "future_self", "podcast", "recruitment_process",
]);

const DESTINATIONS: Record<string, readonly NavEntry[]> = {
  demo: [{ section: "lab", path: "/demo", labelKey: "demo.title", order: 100 }],
};

export function descriptionKey(id: string): MessageKey | undefined {
  return Object.hasOwn(navigation.features, id) ? `navigation.features.${id as Feature}` : undefined;
}

function destinations(feature: FeatureManifest): Destination[] {
  const description = descriptionKey(feature.id);
  if (!description) return [];
  const id = feature.id as Feature;
  return (feature.nav ?? DESTINATIONS[id] ?? []).map((entry) => {
    const section = PRIMARY[id] ?? "lab";
    const settingsArea = section === "settings" ? (AREAS[entry.path] ?? "advanced") : undefined;
    return { ...entry, id, section, description, settingsArea, modelsRequired: NEEDS_MODELS.has(id) };
  });
}

export function buildDestinations(features: FeatureManifest[]): Destination[] {
  return features.flatMap(destinations);
}

export function sectionLanding(section: Section) {
  const definition = SECTIONS.find((candidate) => candidate.section === section);
  if (!definition) throw new Error(section);
  const { path, labelKey } = definition;
  return { path, labelKey };
}

export function navigationGroups(cards: Destination[]): NavGroup[] {
  return SECTIONS.map(({ path, labelKey, ...definition }) => {
    const landing = { path, labelKey };
    const items = cards.filter(
      (card) => card.section === definition.section && card.path !== landing.path,
    );
    return { ...definition, labelKey, landing, items: [landing, ...items] };
  });
}

export function pinnedDestinations(cards: Destination[], pins: string[]): Destination[] {
  return pins.flatMap((id) => {
    const card = cards.find((item) => item.id === id && item.section === "lab");
    return card ? [card] : [];
  });
}
