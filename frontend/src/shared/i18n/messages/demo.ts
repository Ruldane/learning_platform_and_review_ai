/** Textes de la démo du moteur d'agents. */
export const demo = {
  title: "Démo du moteur d'agents",
  intro:
    "Un Avocat et un Critique débattent d'un sujet de ton choix ; l'équipe te pose une question entre les deux tours.",
  topic: {
    label: "Sujet",
    placeholder: "Ex. apprendre Rust",
    submit: "Lancer le débat",
    starting: "Lancement…",
  },
  loading: "Ouverture du débat…",
  reconnecting: "Connexion au direct perdue, reconnexion…",
  restart: "Nouveau débat",
  cancel: {
    title: "Annuler le débat ?",
    description: "Les agents s'arrêtent et la session ne pourra plus reprendre.",
    confirm: "Oui, annuler le débat",
    keep: "Non, continuer",
  },
} as const;
