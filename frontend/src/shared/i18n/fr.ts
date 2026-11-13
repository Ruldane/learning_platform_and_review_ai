import { agents } from "./messages/agents";
import { appMessages } from "./messages/app";
import { capture } from "./messages/capture";
import { demo } from "./messages/demo";
import { learning } from "./messages/learning";
import { lessons } from "./messages/lessons";
import { memory } from "./messages/memory";
import { program } from "./messages/program";
import { quiz } from "./messages/quiz";
import { replan } from "./messages/replan";
import { research } from "./messages/research";
import { session } from "./messages/session";
import { settings } from "./messages/settings";
import { skills } from "./messages/skills";
import { study } from "./messages/study";

/**
 * Tous les textes de l'interface, en français : agrégat des fichiers `messages/<zone>.ts`.
 * Règle : une nouvelle feature ajoute un fichier `messages/<feature>.ts` (`export const <feature>
 * = { … } as const;`) et une ligne ici. `{nom}` marque une variable (voir `t`).
 */
export const fr = {
  ...appMessages,
  session,
  agents,
  demo,
  settings,
  memory,
  research,
  program,
  lessons,
  learning,
  study,
  quiz,
  skills,
  replan,
  capture,
} as const;
