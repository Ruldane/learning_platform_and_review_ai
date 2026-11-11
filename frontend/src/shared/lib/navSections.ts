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
export const NAV_SECTIONS: readonly { id: NavSection; labelKey: MessageKey; icon: LucideIcon }[] = [
  { id: "home", labelKey: "nav.home", icon: Home },
  { id: "learn", labelKey: "nav.learn", icon: BookOpen },
  { id: "study", labelKey: "nav.study", icon: GraduationCap },
  { id: "skills", labelKey: "nav.skills", icon: Sparkles },
  { id: "career", labelKey: "nav.career", icon: Briefcase },
  { id: "applications", labelKey: "nav.applications", icon: Send },
  { id: "memory", labelKey: "nav.memory", icon: Brain },
  { id: "settings", labelKey: "nav.settings", icon: Settings },
];
