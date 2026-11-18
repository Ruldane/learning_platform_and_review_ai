import {
  BookOpen,
  Brain,
  Briefcase,
  GraduationCap,
  Home,
  Send,
  Settings,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import type { MessageKey } from "@/shared/i18n/t";
import type { NavSection } from "./feature";

/** Sections de la navigation latérale, dans l'ordre d'affichage (spec 15.1). */
export interface NavSectionDef {
  id: NavSection;
  labelKey: MessageKey;
  icon: LucideIcon;
  /** Jeton de couleur du thème (voir `index.css`) : repère la section dans le menu et le panneau. */
  color: string;
}

export const NAV_SECTIONS: readonly NavSectionDef[] = [
  { id: "home", labelKey: "nav.home", icon: Home, color: "var(--section-home)" },
  { id: "learn", labelKey: "nav.learn", icon: BookOpen, color: "var(--section-learn)" },
  { id: "study", labelKey: "nav.study", icon: GraduationCap, color: "var(--section-study)" },
  { id: "skills", labelKey: "nav.skills", icon: Sparkles, color: "var(--section-skills)" },
  { id: "career", labelKey: "nav.career", icon: Briefcase, color: "var(--section-career)" },
  {
    id: "applications",
    labelKey: "nav.applications",
    icon: Send,
    color: "var(--section-applications)",
  },
  { id: "memory", labelKey: "nav.memory", icon: Brain, color: "var(--section-memory)" },
  { id: "settings", labelKey: "nav.settings", icon: Settings, color: "var(--section-settings)" },
];
