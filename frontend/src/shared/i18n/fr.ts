import { account } from "./messages/account";
import { agents } from "./messages/agents";
import { applications } from "./messages/applications";
import { appMessages } from "./messages/app";
import { auth } from "./messages/auth";
import { brain } from "./messages/brain";
import { capture } from "./messages/capture";
import { chat } from "./messages/chat";
import { conversations } from "./messages/conversations";
import { costs } from "./messages/costs";
import { cv } from "./messages/cv";
import { demo } from "./messages/demo";
import { gap } from "./messages/gap";
import { home } from "./messages/home";
import { ide } from "./messages/ide";
import { learning } from "./messages/learning";
import { lessons } from "./messages/lessons";
import { mcp } from "./messages/mcp";
import { memory } from "./messages/memory";
import { onboarding } from "./messages/onboarding";
import { program } from "./messages/program";
import { projects } from "./messages/projects";
import { quiz } from "./messages/quiz";
import { radar } from "./messages/radar";
import { reading } from "./messages/reading";
import { replan } from "./messages/replan";
import { research } from "./messages/research";
import { session } from "./messages/session";
import { settings } from "./messages/settings";
import { skills } from "./messages/skills";
import { study } from "./messages/study";
import { training } from "./messages/training";

/**
 * Tous les textes de l'interface, en français : agrégat des fichiers `messages/<zone>.ts`.
 * Règle : une nouvelle feature ajoute un fichier `messages/<feature>.ts` (`export const <feature>
 * = { … } as const;`) et une ligne ici. `{nom}` marque une variable (voir `t`).
 */
export const fr = {
  ...appMessages,
  auth,
  brain,
  account,
  session,
  agents,
  demo,
  settings,
  onboarding,
  memory,
  research,
  program,
  lessons,
  learning,
  study,
  training,
  quiz,
  skills,
  replan,
  capture,
  chat,
  conversations,
  gap,
  costs,
  cv,
  applications,
  home,
  radar,
  reading,
  projects,
  mcp,
  ide,
} as const;
