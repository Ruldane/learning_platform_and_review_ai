/** Textes des réglages (modèles et clés). */
export const settings = {
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
} as const;
