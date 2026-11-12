/** Textes de la session d'étude : minuteur, modes, question du Tuteur, rythme, bloc du jour, bilan. */
export const study = {
  timer: {
    label: "Minuteur d'étude",
    remaining: "Temps restant",
    phase: { work: "Travail", break: "Pause" },
    pause: "Mettre en pause",
    resume: "Reprendre",
    paused: "Minuteur en pause",
    worked: "Temps travaillé : {time}",
    announceBreak: "Pause de {minutes} min : lève-toi, respire, bois un verre d'eau.",
    announceWork: "Fin de la pause : reprise du travail.",
  },
  modes: {
    label: "Mode d'étude",
    socratic: {
      label: "Socratique",
      description: "Le tuteur te guide par des questions : tu trouves la réponse toi-même.",
    },
    feynman: {
      label: "Feynman",
      description: "Tu expliques chaque section avec tes mots, le tuteur repère les trous.",
    },
    direct: {
      label: "Direct",
      description: "Le tuteur explique d'abord, puis te pose les questions.",
    },
  },
  tutor: {
    answerLabel: "Ta réponse",
    answer: "Répondre",
    stuck: "Je bloque",
    skip: "Passer",
    answered: "Réponse envoyée",
  },
  stats: {
    label: "Ton rythme d'étude",
    streakNone: "Pas de série en cours",
    streakOne: "Série : {count} jour",
    streakMany: "Série : {count} jours",
    week: "Cette semaine : {time}",
  },
  block: {
    title: "Ton bloc du jour",
    module: "Module : {module}",
    tasks: "Tâches du bloc",
    total: "{time} au total",
    start: "Commencer mon bloc",
    resume: "Reprendre ma session",
    open: "Une session est déjà ouverte : reprends-la là où tu l'as laissée.",
    emptyTitle: "Rien de prévu pour aujourd'hui",
    emptyDescription:
      "Aucune tâche d'étude n'est à faire : reviens demain ou avance sur le programme.",
  },
  summary: {
    title: "Session terminée",
    context: "{module} : {lesson}",
    minutes: "Temps travaillé",
    tasks: "Tâches cochées",
    noTasks: "Aucune tâche cochée.",
    cards: "Fiches créées",
    cardsOne: "{count} fiche créée pour tes révisions.",
    cardsMany: "{count} fiches créées pour tes révisions.",
    noCards: "Aucune nouvelle fiche.",
    skills: "Acquis mis à jour",
    noSkills: "Aucun acquis mis à jour.",
    level: { declare: "Déclaré", en_cours: "En cours", valide: "Validé", prouve: "Prouvé" },
  },
} as const;
