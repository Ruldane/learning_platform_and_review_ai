import { PERSONA_ORDER } from "./types";
import type { CommitteeRunOut, CommitteeView, PersonaView } from "./types";

const rank = (persona: PersonaView): number => PERSONA_ORDER.indexOf(persona);

/** Une exécution du comité du serveur → la vue de la page (les votes toujours dans l'ordre du comité). */
export function toCommitteeView(out: CommitteeRunOut): CommitteeView {
  return {
    id: out.id,
    cvVersionId: out.cv_version_id,
    postingId: out.posting_id,
    sessionId: out.session_id,
    status: out.status,
    verdict: out.verdict,
    votes: [...out.votes].sort((a, b) => rank(a.persona) - rank(b.persona)),
    objections: out.objections.map(({ text, personas }) => ({ text, personas })),
    changes: out.changes.map(({ text, persona, needs_skill, terms }) => ({
      text,
      persona,
      needsSkill: needs_skill,
      terms,
    })),
    diff: out.previous
      ? {
          votes: [...out.previous.votes].sort((a, b) => rank(a.persona) - rank(b.persona)),
          resolved: out.previous.objections_resolved,
          added: out.previous.objections_new,
        }
      : null,
  };
}
