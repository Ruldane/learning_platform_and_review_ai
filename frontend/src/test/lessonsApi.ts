export { API } from "./councilApi";

/** Une ressource telle que le back la rend (`ResourceOut`). */
export const resourceOut = (over: Record<string, unknown> = {}) => ({
  id: "r1",
  module_id: "m1",
  program_id: "p1",
  title: "Documentation officielle de Python",
  url: "https://docs.python.org/3/tutorial/",
  type: "documentation",
  lang: "en",
  duration_minutes: 45,
  level: "debutant",
  author: "Python Software Foundation",
  date: "2025-10-01",
  reason: "La référence, à jour de la dernière version.",
  note: null,
  score: 92,
  has_local_copy: false,
  status: "to_read",
  ...over,
});

/** Une leçon telle que le back la rend (`LessonOut`). */
export const lessonOut = (over: Record<string, unknown> = {}) => ({
  id: "l1",
  module_id: "m1",
  program_id: "p1",
  title: "Les variables et les types",
  week_rank: 1,
  status: "ready",
  failure_reason: null,
  markdown: "## L'essentiel\n\nUne variable nomme une valeur.\n\n## Exemple\n\nx = 3",
  word_count: 1400,
  pdf_available: true,
  resources: [resourceOut()],
  ...over,
});

/** Une ligne de la liste des leçons d'un programme (`LessonSummaryOut`). */
export const lessonSummary = (over: Record<string, unknown> = {}) => ({
  id: "l1",
  module_id: "m1",
  title: "Les variables et les types",
  week_rank: 1,
  status: "ready",
  word_count: 1400,
  pdf_available: true,
  ...over,
});
