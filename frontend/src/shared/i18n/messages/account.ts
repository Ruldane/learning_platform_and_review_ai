/** Textes de la page « Mes données » : export et suppression de tout le compte (SPEC 17.3). */
export const account = {
  nav: { data: "Mes données" },
  title: "Mes données",
  intro: "Ce que Tremplin garde dans ton espace : tu peux l'emporter, ou tout effacer.",
  export: {
    title: "Exporter",
    description:
      "Une archive zip avec tout ce que ton espace contient : tes réglages, ton profil et ton CV, tes objectifs et ton programme, tes leçons et tes révisions, ta mémoire, tes candidatures et le journal des appels aux modèles, plus les fichiers que tu as importés. Elle ne contient jamais tes clés d'API, ni les vecteurs de la mémoire, que Tremplin recalcule.",
    link: "Exporter toutes mes données",
    help: "Le téléchargement s'ouvre dans un nouvel onglet ; si la session a expiré, reconnecte-toi puis réessaie.",
  },
  delete: {
    title: "Tout supprimer",
    warning: "Cette action est irréversible.",
    scope:
      "Elle efface tout ce que Tremplin garde pour toi : réglages, clés saisies dans l'interface, profil, CV, programme, leçons, mémoire, candidatures, journal des appels et fichiers importés. Exporte d'abord si tu veux en garder une copie.",
    keep: "Les clés d'API écrites dans le fichier .env ne sont pas touchées.",
    after:
      "Avec un compte Google, ton compte Tremplin disparaît aussi et tu reviens à la page de connexion ; sur cet ordinateur seul, tu reviens au premier lancement.",
    word: "SUPPRIMER",
    label: "Tape SUPPRIMER pour confirmer",
    submit: "Tout supprimer",
    pending: "Suppression en cours…",
    confirmationRequired: "Le mot de confirmation n'est pas bon : tape SUPPRIMER, en majuscules.",
    retry: "Tu peux réessayer : la suppression reprend là où elle s'est arrêtée.",
    notStarted: "Rien n'a été supprimé : tu peux réessayer sans risque.",
    waiting: "Suppression en cours… ne ferme pas cette page.",
  },
} as const;
