import type {
  ApplicationView,
  ContactView,
  EventView,
  ReminderView,
  StatsView,
  StatusView,
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
