export const book = {
  title: "Ton livre",
  program: {
    label: "Programme",
    pick: "Sélectionne un programme",
    empty: "Créer un programme depuis un objectif",
  },
  edition: {
    label: "Édition du programme",
    prepare: "Préparer le livre",
    queued: "L’édition est en préparation.",
    failed: "Le livre n’a pas pu être préparé.",
    retry: "Réessayer",
    chapters: "Chapitres publiés dans l’édition : {count}",
  },
  download: {
    pdf: "Télécharger en PDF",
    epub: "Télécharger en EPUB",
  },
  notes: {
    title: "Lier une note Obsidian",
    help: "Ajoute ce lien wiki dans une note synchronisée. Remplace « identifiant » par l’identifiant à la fin de l’adresse de la leçon.",
    link: "[[tremplin:lesson:identifiant]]",
  },
} as const;
