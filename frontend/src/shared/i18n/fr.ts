import { account } from "./messages/account";
import { agents } from "./messages/agents";
import { applications } from "./messages/applications";
import { appMessages } from "./messages/app";
import { auth } from "./messages/auth";
import { book } from "./messages/book";
import { boss } from "./messages/boss";
import { brain } from "./messages/brain";
import { capture } from "./messages/capture";
import { chat } from "./messages/chat";
import { conversations } from "./messages/conversations";
import { codeTrial } from "./messages/codeTrial";
import { contributions } from "./messages/contributions";
import { costs } from "./messages/costs";
import { cv } from "./messages/cv";
import { demo } from "./messages/demo";
import { futureSelf } from "./messages/futureSelf";
import { gap } from "./messages/gap";
import { home } from "./messages/home";
import { ide } from "./messages/ide";
import { learning } from "./messages/learning";
import { lessonHunt } from "./messages/lessonHunt";
import { lessons } from "./messages/lessons";
import { mcp } from "./messages/mcp";
import { memory } from "./messages/memory";
import { messageReview } from "./messages/messageReview";
import { onboarding } from "./messages/onboarding";
import { oncall } from "./messages/oncall";
import { paperLab } from "./messages/paperLab";
import { podcast } from "./messages/podcast";
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
  book,
  boss,
  account,
  session,
  agents,
  demo,
  settings,
  onboarding,
  memory,
  messageReview,
  research,
  program,
  lessonHunt,
  lessons,
  learning,
  study,
  training,
  oncall,
  paperLab,
  podcast,
  quiz,
  skills,
  replan,
  capture,
  chat,
  conversations,
  contributions,
  codeTrial,
  gap,
  costs,
  cv,
  applications,
  home,
  radar,
  futureSelf,
  reading,
  projects,
  mcp,
  ide,
} as const;
