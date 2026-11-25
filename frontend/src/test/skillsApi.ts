import { http, HttpResponse } from "msw";
import { API } from "./councilApi";

/** Un graphe de compétences tel que le back le rend (`SkillGraphOut`). */
export const graphOut = (over: Record<string, unknown> = {}) => ({
  nodes: [
    { id: "s1", name: "HTML", domain: "web", level: "validated", demand: null, evidence_count: 3 },
    { id: "s2", name: "CSS", domain: "web", level: "in_progress", demand: null, evidence_count: 1 },
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
  level: "in_progress",
  evidence: [
    {
      kind: "lesson",
      label: "Leçon : Sélecteurs",
      at: "2026-11-10T09:00:00Z",
      url: "/learn/lessons/l1",
    },
    { kind: "program", label: "Programme web", at: null, url: null },
  ],
  postings: [],
  next_action: { kind: "quiz", label: "Passer le quiz « Mise en page »", url: "/study/quiz/q1" },
  ...over,
});

export const historyOut = () => ({
  points: [
    {
      week_start: "2026-11-09",
      counts: { declared: 1, in_progress: 1, validated: 1, proven: 0 },
      score: 50,
    },
    {
      week_start: "2026-11-16",
      counts: { declared: 0, in_progress: 2, validated: 1, proven: 0 },
      score: 58,
    },
  ],
});

export const compareOut = () => ({
  target_label: "Data engineer",
  coverage: 33,
  rows: [
    { skill_id: "s1", name: "HTML", domain: "web", mine: "proven", target: "validated", gap: -1 },
    { skill_id: "s3", name: "React", domain: "web", mine: null, target: "validated", gap: 3 },
  ],
});

interface SkillsApi {
  graph?: () => Response;
  detail?: () => Response;
  history?: () => Response;
  compare?: (request: Request) => Response;
  /** `GET /postings` : les offres proposées à la comparaison. */
  postings?: () => Response;
}

/** Les quatre lectures de la carte ; `reads.graph` compte les relectures du graphe. */
export function skillsApi(api: SkillsApi = {}) {
  const reads = { graph: 0, detail: 0, postings: 0, compareQueries: [] as string[] };
  const handlers = [
    http.get(`${API}/skills/graph`, () => {
      reads.graph += 1;
      return api.graph?.() ?? HttpResponse.json(graphOut());
    }),
    http.get(`${API}/skills/history`, () => api.history?.() ?? HttpResponse.json(historyOut())),
    http.get(`${API}/skills/compare`, ({ request }) => {
      reads.compareQueries.push(new URL(request.url).search);
      return api.compare?.(request) ?? HttpResponse.json(compareOut());
    }),
    http.get(`${API}/postings`, () => {
      reads.postings += 1;
      return api.postings?.() ?? HttpResponse.json([]);
    }),
    http.get(`${API}/skills/s2`, () => {
      reads.detail += 1;
      return api.detail?.() ?? HttpResponse.json(detailOut());
    }),
  ];
  return { reads, handlers };
}
