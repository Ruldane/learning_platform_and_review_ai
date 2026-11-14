/** Les objets que le back rend pour le profil, les modèles, les revues et les versions de CV (fictifs). */
type Over = Record<string, unknown>;

/** Un profil maître fictif (`MasterProfileData`) : « Camille Exemple », domaines `example.org`. */
export const profileData = (over: Over = {}) => ({
  identity: {
    name: "Camille Exemple",
    email: "camille.exemple@example.org",
    phone: null,
    location: "Lyon",
    headline: null,
  },
  title: { id: "t1", text: "Ingénieure données", sources: ["cv"] },
  summary: { id: "s1", text: "Dix ans de données.", sources: ["cv", "linkedin"] },
  experiences: [
    {
      id: "e1",
      role: "Data engineer",
      company: "Société Fictive",
      location: null,
      start: "2020-01",
      end: null,
      sources: ["cv"],
      achievements: [{ id: "a1x", text: "Pipelines de 2 To par jour" }],
    },
  ],
  education: [],
  skills: [{ id: "k1", name: "Python", category: null, sources: ["cv"] }],
  projects: [],
  languages: [],
  links: [],
  ...over,
});

/** Une version du profil (`ProfileOut`). */
export const profileOut = (over: Over = {}) => ({
  version: 2,
  status: "draft",
  source: "archivist",
  created_at: "2026-11-10T10:00:00Z",
  dropped: [],
  data: profileData(),
  ...over,
});

export const emptyProfile = { draft: null, validated: null, session_id: null };

/** Un modèle de CV (`TemplateOut`) prêt et actif, après deux passes. */
export const templateOut = (over: Over = {}) => ({
  id: "t1",
  name: "Mon CV",
  status: "ready",
  active: true,
  score: 91,
  passes: 2,
  page_count: 1,
  created_at: "2026-11-10T10:00:00Z",
  selectable: true,
  fonts: [],
  font_gaps: ["La police des titres n'est pas libre : remplacée par Carlito, très proche."],
  zones: [{ zone: "haut", original: 0.4, render: 0.3 }],
  session_id: "d1",
  failure_reason: null,
  ...over,
});

/** Une ligne de la liste des modèles (`TemplateSummaryOut`). */
export const templateSummary = (over: Over = {}) => {
  const { id, name, status, active, score, passes, page_count, created_at } = templateOut(over);
  return { id, name, status, active, score, passes, page_count, created_at };
};

export const modificationOut = (id: string, over: Over = {}) => ({
  id,
  ref: "a1",
  section: "experience",
  action: "rewrite",
  type: "impact",
  before: "Pipelines de données",
  after: "Pipelines de 2 To par jour",
  reason: "Le chiffre est dans ton profil.",
  status: "proposed",
  blocks: [],
  fact_ids: ["a1x"],
  author: "ats_reader",
  ...over,
});

export const indicators = (coverage: number, over: Over = {}) => ({
  coverage_percent: coverage,
  covered: 2,
  total: 4,
  missing: ["Kubernetes"],
  checks: [{ id: "selectable_text", passed: true, detail: "Le texte est sélectionnable." }],
  ...over,
});

export const versionOut = (over: Over = {}) => ({
  id: "v1",
  review_id: "rv1",
  posting_id: "p1",
  number: 1,
  status: "ready",
  page_count: 1,
  original_page_count: 1,
  allow_extra_pages: false,
  filename: "CV_Camille_Exemple_Societe_Fictive.pdf",
  decisions: {},
  indicators: indicators(75),
  created_at: "2026-11-11T10:00:00Z",
  failure_reason: null,
  ...over,
});

/** Une revue (`CvReviewOut`) qui attend la décision : une modification à décider, une à confirmer. */
export const reviewOut = (over: Over = {}) => ({
  id: "rv1",
  posting_id: "p1",
  status: "proposed",
  session_id: "r1",
  before: indicators(50),
  modifications: [
    modificationOut("m1"),
    modificationOut("m2", {
      ref: "r1",
      status: "to_confirm",
      blocks: ["Outil absent : Kubernetes."],
      after: "Déploiement sur Kubernetes",
      fact_ids: [],
    }),
  ],
  gap_terms: ["Kubernetes"],
  report: {
    ats: "Greenhouse",
    ats_notes: [],
    company_summary: null,
    strengths: ["Pipelines chiffrés"],
    risks: [],
    eliminatory: [],
  },
  versions: [],
  waiting_output: true,
  created_at: "2026-11-11T09:00:00Z",
  ...over,
});
