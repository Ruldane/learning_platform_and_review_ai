import { t } from "@/shared/i18n/t";

/**
 * One fixed color per agent (SPEC 15.4), used in bubbles, board annotations and
 * logs. The slugs are those of `AgentSpec.name` on the back; those of later phases are
 * reserved here so an agent's color never changes from one screen to another.
 *
 * Each color reaches a contrast of at least 4.5:1 on the off-white background (#FAFAF7), so
 * also white on the color (avatar); `agentColors.test.ts` checks it. The color is not
 * the only signal: the agent's name is always written.
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
  manager: "#0060f0",
  colleague: "#a000f0",
  demo_proponent: "#6834b2",
  demo_critic: "#b2345c",
  professor: "#7a4a1d",
  exercise_writer: "#2d6a4f",
  boss_reviewer: "#59524a",
  code_prosecutor: "#882a34",
  code_defender: "#24526a",
  oncall_reviewer: "#6d3971",
  lesson_professor: "#4c4831",
  training_tutor: "#265e51",
  brain_librarian: "#775338",
  podcast_host: "#5e5088",
  offers_adviser: "#315c79",
} as const;

export type AgentSlug = keyof typeof AGENT_COLORS;

/** Neutral grey (6:1 contrast) for unknown agents. */
export const UNKNOWN_AGENT_COLOR = "#57606a";

export interface AgentIdentity {
  name: string;
  role: string;
  color: string;
}

const isKnownAgent = (slug: string): slug is AgentSlug => Object.hasOwn(AGENT_COLORS, slug);

/** A display name, role, and color. Unknown agents show their slug with a neutral color. */
export function agentIdentity(slug: string): AgentIdentity {
  if (!isKnownAgent(slug)) return { name: slug, role: "", color: UNKNOWN_AGENT_COLOR };
  return {
    name: t(`agents.${slug}.name`),
    role: t(`agents.${slug}.role`),
    color: AGENT_COLORS[slug],
  };
}
