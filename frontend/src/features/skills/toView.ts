import type {
  CompareRowView,
  DomainScoreView,
  HistoryPointView,
  SkillDetailView,
  SkillEdgeView,
  SkillNodeView,
} from "./components/viewTypes";
import type { CompareOut, HistoryOut, SkillDetailOut, SkillGraphOut } from "./types";

/** Le graphe du contrat → les types de vue de la carte (camelCase). */
export function toGraphView(graph: SkillGraphOut): {
  nodes: SkillNodeView[];
  edges: SkillEdgeView[];
  domains: DomainScoreView[];
} {
  return {
    nodes: graph.nodes.map((node) => ({
      id: node.id,
      name: node.name,
      domain: node.domain,
      level: node.level,
      demand: node.demand,
      evidenceCount: node.evidence_count,
    })),
    edges: graph.edges.map((edge) => ({ beforeId: edge.before_id, afterId: edge.after_id })),
    domains: graph.domains.map(({ domain, score }) => ({ domain, score })),
  };
}

/** Le détail d'une compétence ; une preuve sans date (phase 4) garde `at: null`. */
export function toDetailView(detail: SkillDetailOut): SkillDetailView {
  return {
    id: detail.id,
    name: detail.name,
    domain: detail.domain,
    synonyms: detail.synonyms,
    level: detail.level,
    evidence: detail.evidence.map(({ kind, label, at, url }) => ({ kind, label, at, url })),
    postings: detail.postings.map(({ id, title, url }) => ({ id, title, url })),
    nextAction: detail.next_action
      ? {
          kind: detail.next_action.kind,
          label: detail.next_action.label,
          url: detail.next_action.url,
        }
      : null,
  };
}

export function toHistoryView(history: HistoryOut): HistoryPointView[] {
  return history.points.map((point) => ({
    weekStart: point.week_start,
    counts: point.counts,
    score: point.score,
  }));
}

export function toCompareView(compare: CompareOut): {
  rows: CompareRowView[];
  coverage: number;
  targetLabel: string;
} {
  return {
    targetLabel: compare.target_label,
    coverage: compare.coverage,
    rows: compare.rows.map((row) => ({
      skillId: row.skill_id,
      name: row.name,
      domain: row.domain,
      mine: row.mine,
      target: row.target,
      gap: row.gap,
    })),
  };
}
