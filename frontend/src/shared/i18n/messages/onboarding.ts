/** Textes du premier lancement (`/bienvenue`, SPEC 15.5 et 17.3). */
export const onboarding = {
  gate: {
    checking: "Préparation de ton espace…",
    failed: "Impossible de lire tes réglages.",
  },
  page: {
    label: "Premier lancement",
    loading: "Chargement de ton espace…",
    deleted: "Tes données ont été supprimées : Tremplin repart de zéro.",
  },
  steps: {
    counter: "Étape {step} sur {total}",
    previous: "Précédent",
    next: "Suivant",
    later: "Plus tard",
    skipStep: "Passer",
    finish: "Terminer",
    finishing: "Enregistrement…",
    skipAll: "Passer l'accueil",
    blocked: "Corrige les champs signalés avant de terminer.",
    titles: {
      health: "Les services de Tremplin",
      privacy: "Ce qui sort de ta machine",
      key: "Ta clé d'API",
      cv: "Ton CV",
      availability: "Ton temps disponible",
    },
  },
  health: {
    intro:
      "Tremplin s'appuie sur quelques services locaux. Leur état se met à jour tout seul, tu " +
      "n'as rien à faire ici.",
    list: "État des services",
    checking: "Vérification des services…",
    unreachable: "Impossible de lire l'état des services : nouvel essai automatique.",
    ok: "répond",
    down: "ne répond pas",
    services: {
      db: "Base de données",
      llm: "Clé d'un modèle de langage",
      qdrant: "Mémoire vectorielle (Qdrant)",
      ollama: "Modèle d'embeddings (Ollama)",
      searxng: "Recherche web (SearXNG)",
    },
    keyLater: "à configurer à l'étape 3",
    recovered: "{services} : répond de nouveau.",
  },
  embedding: {
    label: "Modèle d'embeddings",
    percent: "{model} : {percent} %",
    ready: "{model} : prêt",
    waiting: "{model} : téléchargement en attente",
    unreadable: "Impossible de lire la progression du modèle : nouvel essai automatique.",
    hint: "Le modèle se télécharge une seule fois ; Tremplin n'en a besoin que pour la mémoire.",
  },
  privacy: {
    intro:
      "Voici, en clair, ce qui quitte ton ordinateur. Tu peux le relire plus tard dans Réglages.",
    table: "Ce qui sort de ta machine",
    data: "Donnée",
    destination: "Destination",
    rows: {
      prompts: {
        data: "Les prompts, qui peuvent contenir ton CV et ton profil",
        destination: "Le fournisseur de modèle que tu choisis",
      },
      searches: {
        data: "Les requêtes de recherche",
        destination: "Les moteurs interrogés par SearXNG",
      },
      rest: {
        data: "Tout le reste (base, vecteurs, fichiers, embeddings)",
        destination: "Reste sur ta machine",
      },
    },
    safeguards: "Ce que Tremplin fait pour limiter ce qui sort",
    search:
      "La recherche retire ton nom, ton e-mail et ton téléphone des requêtes avant de les envoyer.",
    contacts: "Les contacts que tu enregistres se limitent au nom, au rôle et à un lien public.",
    control: "À tout moment, Réglages > Mes données te laisse tout exporter ou tout supprimer.",
  },
  key: {
    intro:
      "La clé d'un fournisseur envoie tes prompts chez lui (étape précédente). Une clé suffit, " +
      "mais elle doit être celle du fournisseur de tes modèles : si tu en donnes une autre, " +
      "Tremplin règle tes modèles sur ce fournisseur.",
    provider: "Fournisseur",
    fromEnv:
      "Une clé est déjà fournie par le fichier .env ({providers}) : tu peux passer à la suite.",
    fromUi: "Une clé est déjà enregistrée ({providers}) : tu peux passer à la suite.",
    moveTo:
      "Tes modèles passeront sur {provider}, le fournisseur de cette clé, en passant à l'étape " +
      "suivante. Tu pourras les changer dans Réglages > Modèles et clés.",
    noPreset:
      "La clé {provider} n'a pas de préréglage de modèles : une fois l'accueil fini, choisis ses " +
      "modèles dans Réglages > Modèles et clés. D'ici là, l'import du CV reste fermé.",
    none: "Aucune clé pour le moment : tu peux en saisir une, ou le faire plus tard dans Réglages.",
    loading: "Chargement des fournisseurs…",
  },
  cv: {
    intro:
      "Ton CV et ton profil LinkedIn (en PDF) servent à écrire ton profil maître. Tu peux " +
      "passer cette étape et le faire plus tard dans Carrière.",
    privacy: "Leur texte part chez le fournisseur de modèle pour être lu.",
    cvLabel: "Ton CV (PDF, 10 Mo au plus)",
    linkedinLabel: "Ton profil LinkedIn (PDF, facultatif)",
    submit: "Importer mes documents",
    pending: "Envoi en cours…",
    done:
      "Tes documents sont envoyés : Tremplin les lit en arrière-plan, " +
      "tu retrouveras ton profil dans Carrière.",
    notPdf: "Ce fichier n'est pas un PDF : choisis un fichier .pdf.",
    tooBig: "Ce fichier dépasse 10 Mo : choisis un PDF plus léger.",
    needCv: "Choisis d'abord ton CV.",
    needKey:
      "Sans clé d'API, Tremplin ne peut pas lire tes documents : " +
      "ajoute d'abord une clé à l'étape 3.",
    goToKey: "Aller à l'étape de la clé",
    chosen: "Fichier retenu : {name}",
    notSent: "Rien n'est envoyé tant que tu n'as pas cliqué sur « Importer mes documents ».",
    linkedinLeftOut: "Ton profil LinkedIn n'a pas été retenu : seul ton CV sera envoyé.",
  },
  availability: {
    intro:
      "Dis combien de temps tu peux consacrer à l'apprentissage. Tu pourras l'ajuster à tout " +
      "moment dans Réglages > Disponibilité et rythme.",
  },
} as const;
