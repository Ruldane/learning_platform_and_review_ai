export { API } from "./councilApi";

/** A resource as the back returns it (`ResourceOut`). */
export const resourceOut = (over: Record<string, unknown> = {}) => ({
  id: "r1",
  module_id: "m1",
  program_id: "p1",
  title: "Documentation officielle de Python",
  url: "https://docs.python.org/3/tutorial/",
  type: "documentation",
  lang: "en",
  duration_minutes: 45,
  level: "beginner",
  author: "Python Software Foundation",
  date: "2025-10-01",
  reason: "La référence, à jour de la dernière version.",
  note: null,
  score: 92,
  has_local_copy: false,
  status: "to_read",
  ...over,
});

/** A lesson as the back returns it (`LessonOut`). */
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
  done_tasks: 0,
  total_tasks: 3,
  completed: false,
  resources: [resourceOut()],
  ...over,
});

/** A row of a program's lesson list (`LessonSummaryOut`). */
export const lessonSummary = (over: Record<string, unknown> = {}) => ({
  id: "l1",
  module_id: "m1",
  title: "Les variables et les types",
  week_rank: 1,
  status: "ready",
  word_count: 1400,
  pdf_available: true,
  done_tasks: 0,
  total_tasks: 3,
  completed: false,
  ...over,
});
