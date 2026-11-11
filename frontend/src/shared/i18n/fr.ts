/**
 * Tous les textes de l'interface, en français, imbriqués par feature.
 * Les tâches suivantes ajoutent leurs blocs ici ; `{nom}` marque une variable (voir `t`).
 */
export const fr = {
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
  sessions: {
    stream: {
      not_found: "Cette session est introuvable.",
      refused: "Le serveur a refusé la connexion au direct de la session.",
      unreachable: "Connexion au direct perdue. Vérifie que Tremplin est démarré, puis réessaie.",
    },
    errors: {
      stale_interrupt: "Cette question a déjà reçu une réponse.",
      interrupt_required: "Réponds d'abord à la question en attente.",
      session_not_resumable: "Cette session ne peut pas reprendre maintenant.",
      session_not_pausable: "Cette session ne peut plus être mise en pause.",
      session_not_cancellable: "Cette session est déjà terminée : rien à arrêter.",
      session_closed: "Cette session est terminée : elle n'accepte plus de message.",
      session_not_found: "Cette session est introuvable.",
      server_stopping: "Le serveur est en train de s'arrêter. Réessaie dans un instant.",
    },
  },
  settings: {
    models: {
      navLabel: "Modèles et clés",
      title: "Modèles et clés",
      intro:
        "Choisis le fournisseur et le modèle de chaque niveau, et enregistre tes clés API. Une seule clé suffit pour faire tourner toute l'application.",
      empty: {
        title: "Aucun fournisseur disponible",
        description: "Le serveur ne propose aucun fournisseur de modèles pour le moment.",
      },
      loading: "Chargement des réglages…",
    },
    keys: {
      title: "Clés API",
      intro: "Une clé n'est jamais affichée en entier : seuls les 4 derniers caractères le sont.",
      last4: "•••• {last4}",
      none: "Aucune clé enregistrée",
      sourceUi: "saisie ici",
      sourceEnv: "fichier .env",
      unreadable: "Clé illisible, ressaisis-la",
      inputLabel: "Clé API {provider}",
      save: "Enregistrer",
      test: "Tester",
      delete: "Supprimer",
      envHint:
        "Cette clé vient du fichier .env : retire-la de ce fichier pour la supprimer. Tu peux la remplacer en en saisissant une ici.",
      lastTestOk: "Dernier test : réussi",
      lastTestFailed: "Dernier test : échoué",
    },
    tiers: {
      title: "Modèle par niveau",
      intro: "Les agents demandent un niveau ; ici tu choisis le modèle derrière chaque niveau.",
      columns: { tier: "Niveau", usage: "Usage", model: "Modèle" },
      providerLabel: "Fournisseur ({tier})",
      modelLabel: "Modèle ({tier})",
      noKeyOption: "{label} (aucune clé)",
      rapide: { label: "Rapide", usage: "Recherche, extraction, modération" },
      standard: { label: "Standard", usage: "Débat, relecture, quiz, tutorat" },
      fort: { label: "Fort", usage: "Planning, rédaction des leçons, entretiens" },
      vision: { label: "Vision", usage: "Capture du design du CV" },
    },
    presets: {
      label: "Préréglages",
      all_haiku: "Tout Haiku",
      haiku_sonnet_strong: "Haiku avec Sonnet pour le niveau fort",
      all_glm: "Tout GLM",
      all_openai: "Tout OpenAI",
      custom: "Personnalisé",
    },
    vision: {
      warning:
        "Le niveau vision pointe vers un modèle sans vision : la capture du design du CV est désactivée.",
    },
  },
} as const;
