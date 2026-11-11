/** Textes de la recherche web (essai de l'Éclaireur). */
export const research = {
  bench: {
    query: "Requête",
    queryHint: "De 2 à 300 caractères.",
    urls: "Adresses supplémentaires",
    urlsHint: "Une adresse par ligne, 5 au plus : l'Éclaireur les lit en plus de sa recherche.",
    submit: "Lancer l'essai",
    busy: "Essai en cours…",
    errors: {
      query: "La requête doit faire de 2 à 300 caractères.",
      urlScheme: "Cette adresse doit commencer par http:// ou https:// : {url}",
      tooManyUrls: "{max} adresses supplémentaires au plus.",
    },
  },
} as const;
