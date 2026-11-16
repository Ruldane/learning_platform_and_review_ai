type Over = Record<string, unknown>;

export const CRITERIA = ["Ventes agrégées par mois", "Un test vérifie le total", "README clair"];

/** L'énoncé d'un projet (`ProjectBriefOut`) fictif. */
export const briefOut = (over: Over = {}) => ({
  title: "Pipeline de ventes",
  objective: "Agréger les ventes de « Société Fictive » par mois.",
  context: "Un export CSV de ventes sans identité réelle.",
  constraints: ["SQL uniquement", "Un test automatique"],
  criteria: CRITERIA,
  deliverable: "either",
  hours: 6,
  ...over,
});

/** Le résultat d'un critère (`CriterionOut`) ; `criterion` est le texte de l'énoncé de même rang. */
export const criterionOut = (index: number, met: boolean, comment = "") => ({
  index,
  criterion: CRITERIA[index - 1] ?? "Critère hors énoncé",
  met,
  comment,
});

/** Une évaluation (`EvaluationOut`) fictive : le premier critère atteint, les autres non. */
export const evaluationOut = (over: Over = {}) => ({
  at: "2026-11-16T10:30:00Z",
  verdict: "to_redo",
  feedback: "Le total n'est pas testé.",
  repo_status: "read",
  results: [
    criterionOut(1, true, "La requête groupe par mois."),
    criterionOut(2, false, "Aucun test trouvé."),
    criterionOut(3, false, "Le README est vide."),
  ],
  ...over,
});

/** Un brouillon (`DraftOut`) fictif. */
export const draftOut = (kind: string, over: Over = {}) => ({
  kind,
  content: `Texte du brouillon ${kind}.`,
  status: "ready",
  entry: null,
  flags: [],
  edited: false,
  ...over,
});

/** L'entrée de projet proposée au profil maître (`ProfileEntryIn`). */
export const entryOut = (over: Over = {}) => ({
  name: "Pipeline de ventes",
  description: "Agrégation mensuelle des ventes.",
  achievements: ["Requêtes SQL optimisées", "Test du total"],
  ...over,
});

/** Les quatre brouillons d'un projet validé, dans l'ordre du serveur. */
export const fourDrafts = (over: Record<string, Over> = {}) => [
  draftOut("cv_line", over.cv_line),
  draftOut("profile_entry", {
    content: "Pipeline de ventes",
    entry: entryOut(),
    ...over.profile_entry,
  }),
  draftOut("linkedin_post", over.linkedin_post),
  draftOut("readme_plan", over.readme_plan),
];

/** Un rendu (`SubmissionOut`) fictif. */
export const submissionOut = (over: Over = {}) => ({
  at: "2026-11-16T10:00:00Z",
  repo_url: "https://example.org/camille/ventes",
  description: "Une requête SQL qui agrège les ventes.",
  screenshots: 0,
  ...over,
});

/** Un projet (`ProjectOut`) fictif : à faire, énoncé écrit, aucun rendu. */
export const projectOut = (id: string, over: Over = {}) => ({
  id,
  module_id: `m-${id}`,
  program_id: "p1",
  title: "Pipeline de ventes",
  status: "todo",
  brief: briefOut(),
  submissions: [],
  evaluation: null,
  drafts: [],
  validated_at: null,
  profile_version: null,
  session_id: null,
  ...over,
});

/** `ProjectSummary` : la ligne du Portfolio d'un projet. */
export const summaryOf = (project: Over, position: number) => {
  const brief = project.brief as { hours: number } | null;
  return {
    id: project.id,
    module_id: project.module_id,
    program_id: project.program_id,
    program_title: "Parcours data",
    week: position + 1,
    rank: 1,
    title: project.title,
    status: project.status,
    hours: brief?.hours ?? null,
    skills: ["SQL"],
    validated_at: project.validated_at,
    profile_version: project.profile_version,
    session_id: project.session_id,
  };
};
