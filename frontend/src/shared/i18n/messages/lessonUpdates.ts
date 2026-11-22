export const lessonUpdates = {
  title: "Veille des versions",
  release: "{name} {version}",
  source: "Consulter le journal de versions",
  compare: "Comparer l’exemple {block}",
  before: "Exemple publié",
  after: "Exemple proposé",
  accept: "Approuver et vérifier la correction",
  retryDraft: "Relancer la préparation",
  retryCheck: "Relancer la vérification",
  state: {
    preparing: "Le Vérificateur prépare la correction…",
    ready: "Correction à valider",
    stale: "La leçon a changé depuis cette proposition.",
    failed: "La correction n’a pas abouti. La leçon publiée reste disponible.",
    checking: "La correction approuvée est en vérification…",
    published: "Correction publiée",
  },
} as const;
