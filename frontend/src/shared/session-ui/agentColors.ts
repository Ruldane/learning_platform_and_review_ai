import { t } from "@/shared/i18n/t";

/**
 * Une couleur fixe par agent (SPEC 15.4), reprise dans les bulles, les annotations du tableau et
 * les journaux. Les slugs sont ceux de `AgentSpec.name` côté back ; ceux des phases suivantes sont
 * réservés ici pour que la couleur d'un agent ne change jamais d'un écran à l'autre.
 *
 * Chaque couleur atteint un contraste d'au moins 4,5:1 sur le fond blanc cassé (#FAFAF7), donc
 * aussi en blanc sur la couleur (avatar) ; `agentColors.test.ts` le vérifie. La couleur n'est
 * jamais le seul signal : le nom de l'agent est toujours écrit.
 */
export const AGENT_COLORS = {
  moderator: "#566e8f",
  strategist: "#4539ac",
  practitioner: "#1b7e1b",
  scout: "#18788b",
  skeptic: "#b82e2e",
  scribe: "#98613a",
  writer: "#932eb8",
  verifier: "#1a7a5a",
  archivist: "#726e1d",
  ats_reader: "#b74e1a",
  recruiter: "#344fb2",
  designer: "#bd28b6",
  analyst: "#2070b6",
  examiner: "#8f6419",
  interviewer: "#ac3982",
  tutor: "#1a7a72",
  tracker: "#5f761e",
  demo_proponent: "#6834b2",
  demo_critic: "#b2345c",
} as const;

export type AgentSlug = keyof typeof AGENT_COLORS;

/** Gris neutre (contraste 6:1) des agents inconnus. */
export const UNKNOWN_AGENT_COLOR = "#57606a";

export interface AgentIdentity {
  name: string;
  role: string;
  color: string;
}

const isKnownAgent = (slug: string): slug is AgentSlug => Object.hasOwn(AGENT_COLORS, slug);

/** Nom, rôle (via `fr.ts`) et couleur d'un agent ; un slug inconnu devient un gris neutre nommé par son slug. */
export function agentIdentity(slug: string): AgentIdentity {
  if (!isKnownAgent(slug)) return { name: slug, role: "", color: UNKNOWN_AGENT_COLOR };
  return {
    name: t(`agents.${slug}.name`),
    role: t(`agents.${slug}.role`),
    color: AGENT_COLORS[slug],
  };
}
