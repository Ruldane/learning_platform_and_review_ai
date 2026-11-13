import { http, HttpResponse } from "msw";
import { API } from "./councilApi";

/** Un graphe de compétences tel que le back le rend (`SkillGraphOut`). */
export const graphOut = (over: Record<string, unknown> = {}) => ({
  nodes: [
    { id: "s1", name: "HTML", domain: "web", level: "valide", demand: null, evidence_count: 3 },
    { id: "s2", name: "CSS", domain: "web", level: "en_cours", demand: null, evidence_count: 1 },
    { id: "s3", name: "React", domain: "web", level: null, demand: null, evidence_count: 0 },
  ],
  edges: [
    { before_id: "s1", after_id: "s2" },
    { before_id: "s2", after_id: "s3" },
  ],
  domains: [{ domain: "web", score: 62 }],
  ...over,
});

/** Le détail de la compétence `s2` (`SkillDetailOut`) avec une preuve ancienne, sans date. */
export const detailOut = (over: Record<string, unknown> = {}) => ({
  id: "s2",
  name: "CSS",
  domain: "web",
  synonyms: [],
  level: "en_cours",
  evidence: [
    {
      kind: "lesson",
      label: "Leçon : Sélecteurs",
      at: "2026-11-10T09:00:00Z",
      url: "/apprendre/lecons/l1",
    },
    { kind: "program", label: "Programme web", at: null, url: null },
  ],
  postings: [],
  next_action: { kind: "quiz", label: "Passer le quiz « Mise en page »", url: "/etudier/quiz/q1" },
  ...over,
});

export const historyOut = () => ({
  points: [
    {
      week_start: "2026-11-09",
      counts: { declare: 1, en_cours: 1, valide: 1, prouve: 0 },
      score: 50,
    },
    {
      week_start: "2026-11-16",
      counts: { declare: 0, en_cours: 2, valide: 1, prouve: 0 },
      score: 58,
    },
  ],
});

export const compareOut = () => ({
  target_label: "Data engineer",
  coverage: 33,
  rows: [
    { skill_id: "s1", name: "HTML", domain: "web", mine: "prouve", target: "valide", gap: -1 },
    { skill_id: "s3", name: "React", domain: "web", mine: null, target: "valide", gap: 3 },
  ],
});

interface SkillsApi {
  graph?: () => Response;
  detail?: () => Response;
  history?: () => Response;
  compare?: () => Response;
}

/** Les quatre lectures de la carte ; `reads.graph` compte les relectures du graphe. */
export function skillsApi(api: SkillsApi = {}) {
  const reads = { graph: 0, detail: 0 };
  const handlers = [
    http.get(`${API}/skills/graph`, () => {
      reads.graph += 1;
      return api.graph?.() ?? HttpResponse.json(graphOut());
    }),
    http.get(`${API}/skills/history`, () => api.history?.() ?? HttpResponse.json(historyOut())),
    http.get(`${API}/skills/compare`, () => api.compare?.() ?? HttpResponse.json(compareOut())),
    http.get(`${API}/skills/s2`, () => {
      reads.detail += 1;
      return api.detail?.() ?? HttpResponse.json(detailOut());
    }),
  ];
  return { reads, handlers };
}
