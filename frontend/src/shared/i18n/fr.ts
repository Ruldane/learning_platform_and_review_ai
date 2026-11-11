import { agents } from "./messages/agents";
import { appMessages } from "./messages/app";
import { demo } from "./messages/demo";
import { memory } from "./messages/memory";
import { research } from "./messages/research";
import { session } from "./messages/session";
import { settings } from "./messages/settings";

/**
 * Tous les textes de l'interface, en français : agrégat des fichiers `messages/<zone>.ts`.
 * Règle : une nouvelle feature ajoute un fichier `messages/<feature>.ts` (`export const <feature>
 * = { … } as const;`) et une ligne ici. `{nom}` marque une variable (voir `t`).
 */
export const fr = { ...appMessages, session, agents, demo, settings, memory, research } as const;
