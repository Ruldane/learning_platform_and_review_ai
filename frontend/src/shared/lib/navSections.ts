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

/** Side-navigation sections, in display order (spec 15.1). */
export interface NavSectionDef {
  id: NavSection;
  labelKey: MessageKey;
  icon: LucideIcon;
  /** Theme color token (see `index.css`): marks the section in the menu and the panel. */
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
