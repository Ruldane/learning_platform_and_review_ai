import type {
  ApplicationView,
  ContactView,
  DebriefDataView,
  EventView,
  ExchangeView,
  InterviewView,
  ReminderView,
  StatsView,
  StatusView,
  VoteView,
} from "./viewTypes";

let counter = 0;

/** Une fiche de test ; chaque champ se remplace. */
export function makeApplication(overrides: Partial<ApplicationView> = {}): ApplicationView {
  counter += 1;
  return {
    id: `a${counter}`,
    company: `Entreprise ${counter}`,
    title: `Poste ${counter}`,
    status: "to_apply",
    channel: null,
    appliedOn: null,
    interviewOn: null,
    nextAction: null,
    nextActionOn: null,
    dueReminders: 0,
    ...overrides,
  };
}

export function makeApplications(): ApplicationView[] {
  return [
    makeApplication({
      id: "acme",
      company: "Acme",
      title: "Data engineer",
      status: "applied",
      appliedOn: "2026-11-03",
      nextAction: "Relancer",
      nextActionOn: "2026-11-20",
      dueReminders: 2,
    }),
    makeApplication({ id: "beta", company: "Beta", title: "Analyste", status: "to_apply" }),
    makeApplication({
      id: "gamma",
      company: "Gamma",
      title: "Chef de projet",
      status: "interview",
      appliedOn: "2026-10-20",
      nextActionOn: "2026-11-18",
      nextAction: "Préparer l'entretien",
    }),
    makeApplication({
      id: "delta",
      company: "Delta",
      title: "Développeuse",
      status: "applied",
      appliedOn: "2026-11-10",
    }),
  ];
}

export function makeContact(overrides: Partial<ContactView> = {}): ContactView {
  counter += 1;
  return {
    id: `c${counter}`,
    name: "Camille Durand",
    role: "Responsable data",
    url: null,
    ...overrides,
  };
}

export function makeReminder(overrides: Partial<ReminderView> = {}): ReminderView {
  return {
    id: "r1",
    applicationId: "acme",
    kind: "linkedin_7",
    dueOn: "2026-11-12",
    company: "Acme",
    title: "Data engineer",
    contact: makeContact(),
    linkedinSearchUrl: null,
    draft: "Bonjour Camille,\n\nJ'ai postulé au poste de Data engineer chez Acme.",
    ...overrides,
  };
}

export function makeEvents(): EventView[] {
  return [
    {
      id: "e2",
      kind: "status",
      at: "2026-11-10T09:30:00Z",
      statusFrom: "to_apply",
      statusTo: "applied",
      text: null,
    },
    {
      id: "e1",
      kind: "created",
      at: "2026-11-03T08:00:00Z",
      statusFrom: null,
      statusTo: null,
      text: null,
    },
    {
      id: "e3",
      kind: "note",
      at: "2026-11-12T10:00:00Z",
      statusFrom: null,
      statusTo: null,
      text: "Appel avec la RH",
    },
  ];
}

export function makeStats(overrides: Partial<StatsView> = {}): StatsView {
  const byStatus = Object.fromEntries(
    (
      [
        "to_apply",
        "applied",
        "followed_up",
        "interview",
        "offer",
        "rejected",
        "no_answer",
        "withdrawn",
      ] as StatusView[]
    ).map((status) => [status, 0]),
  ) as Record<StatusView, number>;
  return {
    byStatus: { ...byStatus, applied: 3, interview: 1, rejected: 1 },
    responseRate: 0.4,
    meanResponseDays: 6.5,
    dueReminders: 2,
    ...overrides,
  };
}

/** Un échange de test : la question `index` (à partir de 0), répondue, notée 4. */
export function makeExchange(index: number, overrides: Partial<ExchangeView> = {}): ExchangeView {
  return {
    index,
    question: `Question ${index + 1} du recruteur ?`,
    answer: `Ma réponse ${index + 1}.`,
    followUp: null,
    followUpAnswer: null,
    note: 4,
    unrated: false,
    ...overrides,
  };
}

/** Un débrief de test : quatre notes, trois points forts, trois points à corriger. */
export function makeDebrief(overrides: Partial<DebriefDataView> = {}): DebriefDataView {
  return {
    scores: [
      { key: "clarity", value: 4 },
      { key: "structure", value: 3 },
      { key: "technical_depth", value: 2 },
      { key: "role_fit", value: 5 },
    ],
    strengths: ["Exemples concrets", "Ton posé", "Résultats chiffrés"],
    fixes: ["Structure plus nette", "Plus de détails techniques", "Une conclusion"],
    weakestIndex: 1,
    improvedAnswer: "Voici une réponse mieux construite.",
    missed: [1],
    expected: [{ index: 1, points: ["Citer le contexte", "Donner le résultat"] }],
    unrated: [],
    ...overrides,
  };
}

/** Un entretien de test : terminé, trois échanges, débrief écrit. */
export function makeInterview(overrides: Partial<InterviewView> = {}): InterviewView {
  return {
    id: "i1",
    applicationId: "a1",
    postingId: null,
    role: null,
    mode: "mixed",
    durationMin: 15,
    questionCount: 4,
    language: "fr",
    sessionId: "s1",
    status: "done",
    exchanges: [makeExchange(0), makeExchange(1, { note: 2 }), makeExchange(2)],
    debrief: makeDebrief(),
    flags: [],
    cardsCreated: 1,
    createdAt: "2026-11-12T10:00:00Z",
    ...overrides,
  };
}

/** Un vote de test. */
export function makeVote(overrides: Partial<VoteView> = {}): VoteView {
  return {
    persona: "ats_reader",
    vote: "yes",
    objection: "Il manque le mot clé Kubernetes.",
    reason: "Le CV se lit bien par un logiciel de tri.",
    ...overrides,
  };
}

/** Les quatre votes d'un comité : 3 oui, 1 non. */
export function makeVotes(): VoteView[] {
  return [
    makeVote({ persona: "ats_reader", vote: "yes", objection: "Mot clé Kubernetes absent." }),
    makeVote({ persona: "recruiter", vote: "yes", objection: "Parcours un peu long." }),
    makeVote({ persona: "manager", vote: "no", objection: "Peu de résultats chiffrés." }),
    makeVote({ persona: "colleague", vote: "yes", objection: "Rien de personnel." }),
  ];
}
