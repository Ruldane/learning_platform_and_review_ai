/**
 * Tous les textes de l'interface, en français, imbriqués par feature.
 * Les tâches suivantes ajoutent leurs blocs ici ; `{nom}` marque une variable (voir `t`).
 */
export const fr = {
  app: {
    name: "Tremplin",
    skipToContent: "Aller au contenu",
    loading: "Chargement…",
    welcome: {
      title: "Bienvenue sur Tremplin",
      intro: "Ta plateforme locale d'apprentissage et de carrière.",
    },
    notFound: {
      title: "Page introuvable",
      back: "Retour à l'accueil",
    },
  },
  errors: {
    generic: "Une erreur est survenue. Réessaie dans un instant.",
    network: "Impossible de joindre le serveur. Vérifie que Tremplin est démarré.",
    retry: "Réessayer",
  },
  settings: {
    keys: {
      last4: "•••• {last4}",
    },
  },
} as const;
