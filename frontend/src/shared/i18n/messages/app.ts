/** Textes du squelette : application, navigation, accueil, état des services, erreurs communes. */
export const appMessages = {
  app: {
    name: "Tremplin",
    skipToContent: "Aller au contenu",
    loading: "Chargement…",
    newTab: "(s'ouvre dans un nouvel onglet)",
    notFound: {
      title: "Page introuvable",
      back: "Retour à l'accueil",
    },
  },
  nav: {
    label: "Navigation principale",
    menu: "Menu",
    home: "Accueil",
    learn: "Apprendre",
    study: "Étudier",
    skills: "Compétences",
    career: "Carrière",
    applications: "Candidatures",
    memory: "Mémoire",
    settings: "Réglages",
  },
  health: {
    label: "État des services",
    loading: "Vérification des services…",
    allOk: "Tous les services répondent",
    degraded: "Certains services ne répondent pas",
    down: "Base de données indisponible",
    unreachable: "Serveur injoignable",
    failing: "{service} : {detail}",
  },
  time: {
    now: "à l'instant",
    minutes: "il y a {count} min",
    hours: "il y a {count} h",
    days: "il y a {count} j",
  },
  errors: {
    generic: "Une erreur est survenue. Réessaie dans un instant.",
    network: "Impossible de joindre le serveur. Vérifie que Tremplin est démarré.",
    retry: "Réessayer",
  },
} as const;
