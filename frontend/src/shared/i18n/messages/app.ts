/** Textes du squelette : application, navigation, accueil, état des services, erreurs communes. */
export const appMessages = {
  app: {
    name: "Tremplin",
    skipToContent: "Aller au contenu",
    loading: "Chargement…",
    notFound: {
      title: "Page introuvable",
      back: "Retour à l'accueil",
    },
  },
  nav: {
    label: "Navigation principale",
    home: "Accueil",
    learn: "Apprendre",
    study: "Étudier",
    skills: "Compétences",
    career: "Carrière",
    applications: "Candidatures",
    memory: "Mémoire",
    settings: "Réglages",
  },
  home: {
    title: "Bienvenue sur Tremplin",
    intro: "Ta plateforme locale d'apprentissage et de carrière.",
    empty: {
      title: "Ton brief du jour arrivera bientôt",
      description:
        "Les premières fonctions de Tremplin apparaîtront ici dès qu'elles seront branchées.",
    },
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
  errors: {
    generic: "Une erreur est survenue. Réessaie dans un instant.",
    network: "Impossible de joindre le serveur. Vérifie que Tremplin est démarré.",
    retry: "Réessayer",
  },
} as const;
